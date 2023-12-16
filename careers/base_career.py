class BaseCareer:
    def __init__(self, name, profile):
        self.name = name
        self.profile = profile
        self.knowledges = {}
        self.memories = []
        self.skills = []
        self.actions = []

    def msg(self, message):
        response = "response"
        return response

    def add_knowledges(self, index, content):
        self.knowledges[index] = content

    def add_momory(self, memory):
        self.memories.append(memory)

    def add_skill(self, skill):
        self.skills.append(skill)

    def add_action(self, action):
        self.actions.append(action)