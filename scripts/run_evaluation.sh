{\rtf1\ansi\ansicpg936\cocoartf2821
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 #!/bin/bash\
\
echo "Running auto_eval_attribute.py..."\
python src/data_process/auto_eval_attribute.py\
\
echo "Running auto_eval_filter.py..."\
python src/data_process/auto_eval_filter.py\
\
echo "Running auto_eval_sort.py..."\
python src/data_process/auto_eval_sort.py\
\
echo "Running strict_rule_eval_overall.py..."\
python src/data_process/strict_rule_eval_overall.py\
\
echo "All evaluation scripts executed successfully."}