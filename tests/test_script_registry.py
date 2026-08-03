"""
Testes do ScriptRegistry -- o catálogo central de scripts.

Ele é a fonte única que a GUI usa pra montar os cards (nome, ícone,
cor via categoria) e que o AutomationController usa pra instanciar os
scripts. Um descriptor inconsistente aqui quebra os dois lados.
"""

import pytest

from src.services.bot.bot_engine import BotEngine
from src.services.bot.script_registry import (
    ScriptDescriptor,
    ScriptRegistry,
)


def test_todos_os_scripts_nativos_registrados():
    keys = {d.key for d in ScriptRegistry.all()}
    assert keys == {
        "attack", "potion", "pet", "buff", "helper", "fairy",
        "revive", "delete", "bc", "hollow", "sell", "dr_lure",
    }


def test_get_retorna_descriptor_correto():
    descriptor = ScriptRegistry.get("attack")
    assert descriptor.display_name == "Attack"
    assert descriptor.category == "combat"
    assert descriptor.has_config is True


def test_get_de_chave_inexistente_retorna_none():
    assert ScriptRegistry.get("nao_existe") is None


def test_display_names_sao_unicos():
    """
    A GUI indexa COLORS/ICONS por display_name; nomes repetidos fariam
    um script sobrescrever silenciosamente o outro.
    """
    names = [d.display_name for d in ScriptRegistry.all()]
    assert len(names) == len(set(names))


def test_create_instance_repassa_config_para_quem_declara():
    config = {"keys": ["1", "2"], "speed": 200}
    script = ScriptRegistry.create_instance("attack", config)
    assert script._config == config


def test_create_instance_sem_config_usa_dict_vazio():
    script = ScriptRegistry.create_instance("attack", None)
    assert script._config == {}


def test_create_instance_ignora_config_de_quem_nao_declara():
    """Scripts com has_config=False são instanciados sem argumentos."""
    script = ScriptRegistry.create_instance("bc", {"irrelevante": True})
    assert script.name == "BC"


def test_create_instance_de_chave_inexistente_levanta():
    with pytest.raises(KeyError):
        ScriptRegistry.create_instance("nao_existe")


def test_instancias_respeitam_o_protocolo_bot_script():
    """
    Todo script registrado precisa ter .name e .tick -- é o contrato
    que o BotEngine assume ao iterar os scripts no loop.
    """
    for descriptor in ScriptRegistry.all():
        script = ScriptRegistry.create_instance(descriptor.key, {})
        assert isinstance(script.name, str) and script.name
        assert callable(script.tick)


def test_name_da_instancia_bate_com_o_display_name():
    """
    O gating do BotEngine casa script.name com a chave das flags, que a
    GUI monta a partir do display_name do descriptor. Se os dois
    divergirem, o script nunca liga -- ou nunca desliga.
    """
    for descriptor in ScriptRegistry.all():
        script = ScriptRegistry.create_instance(descriptor.key, {})
        assert script.name == descriptor.display_name, (
            f"{descriptor.key}: instância diz '{script.name}', "
            f"descriptor diz '{descriptor.display_name}'"
        )


def test_gating_funciona_com_os_nomes_reais_do_registro():
    """
    Amarra as duas pontas: liga só o Attack usando exatamente os nomes
    que a GUI usaria, e confirma que nenhum outro script é habilitado.
    """
    class Flag:
        def __init__(self, v): self._v = v
        def get(self): return self._v

    feature_enabled = {d.display_name: Flag(d.key == "attack")
                       for d in ScriptRegistry.all()}

    enabled = [d.display_name for d in ScriptRegistry.all()
               if BotEngine.is_script_enabled(d.display_name, feature_enabled)]

    assert enabled == ["Attack"]


def test_register_sobrescreve_pela_chave():
    """Registrar a mesma chave duas vezes substitui, não duplica."""
    original = ScriptRegistry.get("attack")
    try:
        class Dummy:
            name = "Attack"
            def tick(self, **kwargs): return False

        ScriptRegistry.register(
            ScriptDescriptor("attack", "Attack", "X", "combat", Dummy)
        )
        assert ScriptRegistry.get("attack").script_class is Dummy
        assert len([d for d in ScriptRegistry.all() if d.key == "attack"]) == 1
    finally:
        ScriptRegistry.register(original)
