
import random
import openai
import json
import numpy as np
import math

from matplotlib.pyplot import imread
from openai import OpenAI
from tqdm import tqdm
import re
import multiprocessing
from dotenv import load_dotenv
import os
load_dotenv()

def annotate_data(start, end,test_data,return_dict):
    out_list_local = []
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )
    for i in range(start, end):
        temp = 0
        # print(test_data[i]['ques'])
        if temp == 0:
            for j in range(10):
                if temp == 1:
                    break
                try:
                    result3 = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system",
                             "content": '''You are a helpful assistant.'''},
                            {
                                "role": "user",
                                "content": (
                                        '''Please break down the prompt into three subprompts according to the following aspects:

1. **Product attribute** – including brand, model, price range, color, size, weight, or unique features. Use your knowledge of the product.
2. **Filter conditions** – such as minimum customer rating (e.g., 4.0+), number of reviews, shipping options, arrival time (e.g., released in last 30/90 days), return policies, or warranty.
3. **Sorting preferences** – e.g., by lowest price, highest rating, newest arrival, or best-seller ranking.

Important instructions:
- **Each subprompt MUST explicitly include the product name**.
- If a category (1, 2, or 3) is not mentioned in the prompt, return `None` for that subprompt.

---

### Examples:

**Prompt:**  
Search an Xbox Wireless controller with green color and rated above 4 stars.  
**Answer:**  
- Xbox Wireless controller with green color  
- Xbox Wireless controller rated above 4 stars  
- None

**Prompt:**  
Find a premium yoga mat that is at least 6mm thick, has anti-slip design, priced between $30–$70, rated 4.5+ stars with at least 300 reviews, free shipping, and best-seller rank top 10.  
**Answer:**  
- Premium yoga mat with at least 6mm thickness, anti-slip design, and priced between $30–$70  
- Premium yoga mat rated above 4.5 stars based on 300+ reviews and includes free shipping  
- Premium yoga mat ranked in top 10 best-sellers in its category

---

**Prompt:** '''+
test_data[i]['ques']+
'''
**Answer:**
'''
                                )
                            },
                        ],
                        temperature=0,
                        max_tokens=1500
                    )
                    temp = 1
                except:
                    temp = 0
        if temp == 0:
            print("out of try")
            break

        out_list_local.append(result3.choices[0].message.content)


    return_dict[start] = out_list_local


def split_string(input_string):
    parts = input_string.strip().split('\n')
    return [part.lstrip('- ').strip() for part in parts]




if __name__ == "__main__":
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    test_data=[]
    with open("./data/deepshop_evol_600.jsonl", 'r', encoding="utf-8") as f:
        for line in f:
            temp = json.loads(line)
            test_data.append(temp)
    print(len(test_data))
    processes = []
    num_data=600
    num_processes =20
    data_per_process =  num_data // num_processes
    start_index_lst=[]
    for idx in range(num_processes):
        start_index = idx * data_per_process
        start_index_lst.append(start_index)
        end_index = (idx + 1) * data_per_process
        p = multiprocessing.Process(target=annotate_data, args=(start_index, end_index,test_data,return_dict))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()
    out_data=[]
    for i in start_index_lst:
        out_data+=return_dict[i]
    out_put=[]
    for i in range(len(out_data)):
        temp=split_string(out_data[i])
        test_data[i]['attribute']=temp[0]
        test_data[i]['filter']=temp[1]
        test_data[i]['sort']=temp[2]

    with open('./data/deepshop_evol_600_subquery.jsonl', 'w', encoding='utf-8') as f:
        for entry in test_data:
            json_line = json.dumps(entry, ensure_ascii=False)
            f.write(json_line + '\n')
