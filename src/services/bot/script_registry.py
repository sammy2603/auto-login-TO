from __future__ import annotations

from dataclasses import dataclass
from typing import Type


@dataclass(frozen=True)
class ScriptDescriptor:
    """
    Descreve um Script disponível na plataforma: identidade (chave
    interna, nome de exibição), aparência (ícone, categoria visual) e
    a classe que implementa o comportamento (protocolo BotScript, ver
    bot_engine.py).

    Importante: esta camada (services/bot) não conhece a UI. A
    'category' é só um rótulo semântico (ex: "combat", "support") --
    quem decide qual cor cada categoria vira é a própria UI (ver
    CATEGORY_COLORS em main_window.py). Isso evita que o catálogo de
    scripts dependa da paleta de cores de uma interface específica.
    """

    key: str
    display_name: str
    icon: str
    category: str
    script_class: Type
    has_config: bool = False


class ScriptRegistry:
    """
    Catálogo central de todos os Scripts da plataforma.

    Antes da introdução deste registro, adicionar um script novo
    exigia editar manualmente pelo menos 4 lugares diferentes
    (FEATURES, COLORS e ICONS em main_window.py, além do registro
    dentro do AutomationController). Agora, é só adicionar UMA linha
    em register_builtin_scripts() -- nenhum outro arquivo do sistema
    precisa saber, de antemão, quais scripts existem.
    """

    _descriptors: dict[str, ScriptDescriptor] = {}

    @classmethod
    def register(cls, descriptor: ScriptDescriptor):
        cls._descriptors[descriptor.key] = descriptor

    @classmethod
    def all(cls) -> list[ScriptDescriptor]:
        return list(cls._descriptors.values())

    @classmethod
    def get(cls, key: str) -> ScriptDescriptor | None:
        return cls._descriptors.get(key)

    @classmethod
    def create_instance(cls, key: str, config: dict | None = None):
        """
        Instancia a classe do script registrado sob 'key'. Scripts que
        declaram has_config=True recebem 'config'; os demais são
        instanciados sem argumentos.
        """

        descriptor = cls.get(key)

        if descriptor is None:
            raise KeyError(f"Script não registrado: {key!r}")

        if descriptor.has_config:
            return descriptor.script_class(config=config or {})

        return descriptor.script_class()


def register_builtin_scripts():
    """
    Registra todos os scripts nativos da plataforma. Executado uma
    única vez, na importação deste módulo (ver final do arquivo).

    Para adicionar um script novo: crie a classe em
    src/services/bot/scripts/, e adicione UMA linha de registro aqui.
    Nenhum outro arquivo (GUI, AutomationController) precisa ser
    tocado.
    """

    from src.services.bot.scripts.attack import AttackScript
    from src.services.bot.scripts.potion import PotionScript
    from src.services.bot.scripts.pet_food import PetScript
    from src.services.bot.scripts.buff import BuffScript
    from src.services.bot.scripts.helper import HelperScript
    from src.services.bot.scripts.fairy import FairyScript
    from src.services.bot.scripts.revive import ReviveScript
    from src.services.bot.scripts.delete import DeleteScript
    from src.services.bot.scripts.bc import BCScript
    from src.services.bot.scripts.hollow import HollowScript
    from src.services.bot.scripts.sell import SellScript
    from src.services.bot.scripts.dr_lure import DRLureScript

    ScriptRegistry.register(ScriptDescriptor("attack", "Attack", "\u2694", "combat", AttackScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("potion", "Potion", "\u2697", "support", PotionScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("pet", "Pet", "\u2665", "companion", PetScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("buff", "Buff", "\u21E7", "highlight", BuffScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("helper", "Helper", "\u2699", "utility", HelperScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("fairy", "Fairy", "\u2726", "companion", FairyScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("revive", "Revive", "\u2715", "combat", ReviveScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("delete", "Delete", "\u2717", "neutral", DeleteScript, has_config=False))
    ScriptRegistry.register(ScriptDescriptor("bc", "BC", "\u25C6", "special", BCScript, has_config=True))
    ScriptRegistry.register(ScriptDescriptor("hollow", "Hollow", "\u25CE", "companion", HollowScript, has_config=False))
    ScriptRegistry.register(ScriptDescriptor("sell", "Sell", "\u25C8", "highlight", SellScript, has_config=False))
    ScriptRegistry.register(ScriptDescriptor("dr_lure", "DR Lure", "\u25C9", "companion", DRLureScript, has_config=False))


register_builtin_scripts()