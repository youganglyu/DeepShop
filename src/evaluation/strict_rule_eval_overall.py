import numpy as np
import json
test_file='example'

test_data=[]


with open("./data/deepshop_example.jsonl", 'r', encoding="utf-8") as f:
    for line in f:
        temp = json.loads(line)
        test_data.append(temp)

att_result=np.load('./results/'+test_file+'_attribute.npy')
filter_result=np.load('./results/'+test_file+'_filter.npy')
sort_result=np.load('./results/'+test_file+'_sort.npy')

final_result=[]
att_p=0
filter_p=0
sort_p=0

for i in range(len(test_data)):
    temp_result=1
    if test_data[i]['attribute']!='None':
        temp_result=temp_result*att_result[att_p]
        att_p+=1
    if test_data[i]['filter']!='None':
        temp_result = temp_result * filter_result[filter_p]
        filter_p+=1
    if test_data[i]['sort']!='None':
        temp_result = temp_result * sort_result[sort_p]
        sort_p+=1
    final_result.append(temp_result)
final_result=np.array(final_result)
success_count = sum(final_result)
total_count = len(final_result)
accuracy = (success_count / total_count) * 100
print(f"Overll Acc: {accuracy:.2f}")
np.save('./results/'+test_file +"_overall"+ '.npy', final_result)
