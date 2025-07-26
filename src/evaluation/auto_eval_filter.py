import argparse
import os
import json
import time
import re
import base64
import numpy as np
import multiprocessing
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

SYSTEM_PROMPT = """As an evaluator, you will be presented with three primary components to assist you in your role:

1. Web Task Instruction: A clear and precise natural language directive that specifies an online shopping activity to be executed. The instruction may involve locating products that meet certain attribute requirements (e.g., color, size, brand), applying specific search filters (e.g., price range, customer ratings, availability), or fulfilling user-defined sorting preferences (e.g., lowest price, newest arrivals, best sellers). Tasks may also include verifying product details, comparing offers, or checking for shipping and return policies, depending on the scenario.

2. Result Screenshots: This is a visual representation of the screen showing the result or intermediate state of performing a web task. It serves as visual proof of the actions taken in response to the instruction.

3. Result Response: This is a textual response obtained after the execution of the web task. It serves as textual result in response to the instruction.

-- You DO NOT NEED to interact with web pages or perform actions such as booking flights or conducting searches on websites.
-- You SHOULD NOT make assumptions based on information not presented in the screenshot when comparing it to the instructions.
-- Your primary responsibility is to conduct a thorough assessment of the web task instruction against the outcome depicted in the screenshot and in the response, evaluating whether the actions taken align with the given instructions.
-- NOTE that the instruction may involve more than one task, for example, locating the garage and summarizing the review. Failing to complete either task, such as not providing a summary, should be considered unsuccessful.
-- NOTE that the screenshot is authentic, but the response provided by LLM is generated at the end of web browsing, and there may be discrepancies between the text and the screenshots.
-- Note the difference: 1) Result response may contradict the screenshot, then the content of the screenshot prevails, 2) The content in the Result response is not mentioned on the screenshot, choose to believe the content.

You should elaborate on how you arrived at your final evaluation and then provide a definitive verdict on whether the task has been successfully accomplished, either as 'SUCCESS' or 'NOT SUCCESS'."""

USER_PROMPT = """TASK: <task>
Result Response: <answer>
<num> screenshots at the end: """


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def auto_eval_by_gpt4v_submetric_mp_filter(start, end,test_name,test_data, api_model, img_num,return_dict):
    out_list_local = []
    openai_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL")
    )

    for i in range(start, end):
        process_dir = os.path.join('./results/'+test_name+'/', 'task' + test_data[i]['id'])
        print(f'--------------------- {process_dir} ---------------------')
        res_files = sorted(os.listdir(process_dir))

        with open(os.path.join(process_dir, 'interact_messages.json')) as fr:
                it_messages = json.load(fr)

        if test_data[i]['filter']=="None":
            # out_list_local.append(1)
            continue

        if len(it_messages) == 1:
            print('Not find answer for ' + process_dir + ' only system messages')
            out_list_local.append(0)
            continue

        task_info = it_messages[1]["content"]
        if type(task_info) == list:
            task_info = task_info[0]["text"]

        assert 'Now given a task' in task_info
        pattern = r"Now given a task:(.+?)Please interact with"
        matches = re.search(pattern, task_info)
        task_content = matches.group(1).strip()
        ans_info = it_messages[-1]["content"]
        if 'Action: ANSWER' not in ans_info:
            print('Not find answer for ' + process_dir)
            out_list_local.append(0)
            continue
        pattern_ans = r"ANSWER[; ]+\[?(.[^\]]*)\]?"
        matches_ans = re.search(pattern_ans, ans_info)
        answer_content = matches_ans.group(1).strip()
        whole_content_img = []
        pattern_png = r'screenshot(\d+)\.png'
        matches = [(filename, int(re.search(pattern_png, filename).group(1))) for filename in res_files if re.search(pattern_png, filename)]
        matches.sort(key=lambda x: x[1])
        end_files = matches[-img_num:]
        for png_file in end_files:
            b64_img = encode_image(os.path.join(process_dir, png_file[0]))
            whole_content_img.append(
                {
                    'type': 'image_url',
                    'image_url': {"url": f"data:image/png;base64,{b64_img}"}
                }
            )
        user_prompt_tmp = USER_PROMPT.replace('<task>', test_data[i]['filter'])
        user_prompt_tmp = user_prompt_tmp.replace('<answer>', answer_content)
        user_prompt_tmp = user_prompt_tmp.replace('<num>', str(img_num))
        messages = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': user_prompt_tmp}
                ]
                + whole_content_img
                + [{'type': 'text', 'text': "Your verdict:\n"}]
            }
        ]
        while True:
            try:
                print('Calling gpt4v API to get the auto evaluation......')
                openai_response = openai_client.chat.completions.create(
                    model=api_model, messages=messages, max_tokens=1000, seed=42, temperature=0
                )
                print('Prompt Tokens:', openai_response.usage.prompt_tokens, ';',
                      'Completion Tokens:', openai_response.usage.completion_tokens)
                print('Cost:', openai_response.usage.prompt_tokens/1000 * 0.01
                      + openai_response.usage.completion_tokens / 1000 * 0.03)

                print('API call complete...')
                break
            except Exception as e:
                print(e)
                if type(e).__name__ == 'RateLimitError':
                    time.sleep(10)
                elif type(e).__name__ == 'APIError':
                    time.sleep(15)
                elif type(e).__name__ == 'InvalidRequestError':
                    exit(0)
                else:
                    time.sleep(10)
        gpt_4v_res = openai_response.choices[0].message.content
        print_message = messages[1]
        for idx in range(len(print_message['content'])):
            if print_message['content'][idx]['type'] == 'image_url':
                print_message['content'][idx]['image_url'] = {"url": "data:image/png;base64, b64_img"}

        auto_eval_res = 0 if 'NOT SUCCESS' in gpt_4v_res else 1
        if 'SUCCESS' not in gpt_4v_res:
            auto_eval_res = 0
        out_list_local.append(auto_eval_res)
    return_dict[start] = out_list_local


if __name__ == '__main__':
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    parser = argparse.ArgumentParser()
    parser.add_argument('--process_dir', type=str, default='results')
    parser.add_argument('--lesson_dir', type=str, default='results')
    parser.add_argument("--api_key", default="key", type=str, help="YOUR_OPENAI_API_KEY")
    parser.add_argument("--api_model", default="gpt-4o", type=str, help="api model name")
    parser.add_argument("--max_attached_imgs", type=int, default=15)
    parser.add_argument("--test_name", default="example", type=str, help="test model name")

    args = parser.parse_args()
    data_file = os.path.join('./data/deepshop_example.jsonl')
    domains = []
    test_data = []
    ids = []
    with open(data_file, 'r', encoding="utf-8") as f:
        for line in f:
            temp = json.loads(line)
            test_data.append(temp)
            ids.append(temp['id'])

    processes = []
    num_data =10
    num_processes = 2
    data_per_process = num_data // num_processes
    start_index_lst = []
    for idx in range(num_processes):
        start_index = idx * data_per_process
        start_index_lst.append(start_index)
        end_index = (idx + 1) * data_per_process
        p = multiprocessing.Process(target=auto_eval_by_gpt4v_submetric_mp_filter, args=(
        start_index, end_index, args.test_name, test_data, args.api_model, args.max_attached_imgs, return_dict))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    out_data = []

    for i in start_index_lst:
        out_data += return_dict[i]
    success_count = sum(out_data)
    total_count = len(out_data)
    accuracy = (success_count / total_count) * 100
    print(f"Filter Acc: {accuracy:.2f}")
    domains = np.array(out_data)
    np.save('./results/'+args.test_name +"_filter"+ '.npy', out_data)
