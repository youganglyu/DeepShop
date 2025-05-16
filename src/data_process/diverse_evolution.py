import random

base_instruction = "I want you act as a Prompt Creator.\r\n\
Your goal is to draw inspiration from the #Given Prompt# to create a brand new prompt.\r\n\
This new prompt should be in the web shopping domain but tailored for different specific products in the {} amazon product field.\r\n\
The LENGTH and complexity of the #Created Prompt# should be similar to that of the #Given Prompt#.\r\n\
The #Created Prompt# must be reasonable and must be understood and responded by humans.\r\n\
'#Given Prompt#', '#Created Prompt#', 'given prompt' and 'created prompt' are not allowed to appear in #Created Prompt#\r\n"

def brodenProductPrompt(instruction,category):
	prompt = base_instruction.format(category)
	prompt += "#Given Prompt#: \r\n {} \r\n".format(instruction)
	prompt += "#Created Prompt#:\r\n"
	return prompt