base_instruction = "I want you act as a Prompt Rewriter for web shopping.\r\n \
					Your objective is to rewrite a given prompt into a more complex version to make those web shopping agents a bit harder to handle.\r\n \
					But the rewritten prompt must be reasonable and must be understood and responded by humans.\r\n \
					You should complicate the given prompt using the following method: \r\n\
					{} \r\n\
					You should try your best not to make the #Rewritten Prompt# become verbose, #Rewritten Prompt# can only add 10 to 20 words into #The Given Prompt#. \r\n\
					'#The Given Prompt#', '#Rewritten Prompt#', 'given prompt' and 'rewritten prompt' are not allowed to appear in #Rewritten Prompt#\r\n"


def deepAttributePrompt(instruction):
	prompt = base_instruction.format("Enhance #The Given Prompt# by integrating detailed product attributes that detail user needs. " +
    "Please specifies concrete values for one product attribute (e.g., brand, model, price range, color, size, weight, or unique features) based on your knowledge about this product," +
    "ensure that these exact details are incorporated into the query instead of using generic placeholder terms.")
	prompt += "#The Given Prompt#: \r\n {} \r\n".format(instruction)
	prompt += "#Rewritten Prompt#:\r\n"
	return prompt

def deepConstrainPrompt(instruction):
	prompt = base_instruction.format("Enhance #The Given Prompt# by integrating detailed product constraints that capture user needs. " +
    "Please specifies concrete values for constraints—such as a minimum customer rating (e.g., above 4.0 or 4.5 stars), a minimum number of customer reviews (e.g., 100, 300, 500, or 1000), shipping options like free delivery, new arrival time frames (e.g., released in the last 30 or 90 days), return policies (e.g., free returns), or warranty information (e.g., includes a 1-year warranty) based on your knowledge about amazon website," +
    "ensure that these exact values are used in the query rather than generic terms.")
	prompt += "#The Given Prompt#: \r\n {} \r\n".format(instruction)
	prompt += "#Rewritten Prompt#:\r\n"
	return prompt

def deepToprankPrompt(instruction):
	prompt = base_instruction.format("Enhance #The Given Prompt# by integrating a specific product filtering requirement for web shopping. " +
    "Find the top product based on one of the following criteria: lowest price, highest user rating, " +
    "newest arrival, or best seller ranking.")
	prompt += "#The Given Prompt#: \r\n {} \r\n".format(instruction)
	prompt += "#Rewritten Prompt#:\r\n"
	return prompt