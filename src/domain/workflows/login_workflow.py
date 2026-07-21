from src.domain.workflows.base_workflow import BaseWorkflow


class LoginWorkflow(BaseWorkflow):
    """
    Workflow responsável pelo login automático.
    """

    def execute(self) -> None:
        print("Executing Login Workflow...")