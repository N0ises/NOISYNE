from noisyne.agents.assistant import AssistantAgent
from noisyne.agents.mastering_agent import MasteringAgent
from noisyne.agents.mixing_agent import MixingAgent


class AgentManager:
    """
    Selects and executes the appropriate agent.
    """

    def __init__(self):

        self.assistant = AssistantAgent()
        self.mastering = MasteringAgent()
        self.mixing = MixingAgent()

    def select_agent(self, question):

        question = question.lower()

        mastering_keywords = [
            "master",
            "mastering",
            "lufs",
            "true peak",
            "limiter",
            "loudness",
            "streaming",
        ]

        mixing_keywords = [
            "mix",
            "mixing",
            "eq",
            "compressor",
            "compression",
            "reverb",
            "delay",
            "stereo",
            "balance",
            "panning",
            "sidechain",
        ]

        if any(word in question for word in mastering_keywords):
            return self.mastering

        if any(word in question for word in mixing_keywords):
            return self.mixing

        return self.assistant

    def run(self, question):

        agent = self.select_agent(question)

        return agent.run(question)