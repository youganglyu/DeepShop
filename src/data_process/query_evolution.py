import json
import random
from openai_access import call_chatgpt
from complex_evolution import deepAttributePrompt, deepConstrainPrompt, deepToprankPrompt
from diverse_evolution import brodenProductPrompt

test_seed=[]
product_category=[]
with open('../../data/shopping_seed.jsonl', 'r', encoding="utf-8") as f:
    for line in f:
        temp = json.loads(line)
        test_seed.append(temp["ques"])
        product_category.append(temp["category"])

all_fileds=['Electronics','Fashion', 'Home', 'Books', 'Sports']
#Diversity evolution
for i in range(50):
    instruction = test_seed[i]
    category=random.choice(all_fileds)
    selected_evol_prompt = brodenProductPrompt(instruction,category)
    evol_instruction = call_chatgpt(selected_evol_prompt)
    test_seed.append(evol_instruction)
    product_category.append(category)
initial_seed=test_seed.copy()
test_out=[]

#Complexity evolution
temp_list=[]
for j in range(5):
    for i in range(len(test_seed)):
        instruction=test_seed[i]
        evol_prompts = []
        evol_prompts.append(deepAttributePrompt(instruction))
        evol_prompts.append(deepConstrainPrompt(instruction))
        evol_prompts.append(deepToprankPrompt(instruction))

        selected_evol_prompt = random.choice(evol_prompts)
        evol_instruction = call_chatgpt(selected_evol_prompt)
        temp_list.append(evol_instruction)
        test_out.append(evol_instruction)
    test_seed=temp_list
    temp_list=[]


product_category=product_category*5
difficulty=['easy']*200+['medium']*200+['hard']*200

final_out=[]
test_out=initial_seed+test_out

for i in range(len(test_out)):
    temp={"web_name": "Amazon", "id": "Amazon--"+str(i),
     "ques": test_out[i],
     "web": "https://www.amazon.com/?language=en_US&currency=USD","category": product_category[i],'difficulty':difficulty[i]}
    final_out.append(temp)

with open('../../data/deepshop_evol_600.jsonl', 'w', encoding='utf-8') as f:
    for entry in final_out:
        json_line = json.dumps(entry, ensure_ascii=False)
        f.write(json_line + '\n')




