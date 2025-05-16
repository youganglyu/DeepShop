# **DeepShop: A Benchmark for Deep Research Shopping Agents**



![framework](./assets/framework.jpg)

## Abstract

Web agents for online shopping have shown great promise in automating user interactions across e-commerce platforms. Benchmarks for assessing such agents do not reflect the complexity of real-world shopping scenarios, as they often consist of overly simple queries with deterministic paths, such as “Find iPhone 15.” Real shopping scenarios are inherently more layered, involving multi-dimensional product attributes, search filters, and user-specific sorting preferences. To address this gap, we introduce DeepShop, a benchmark designed to evaluate web agents in complex and realistic online shopping environments. DeepShop comprises three key components. (1) Query diversity evolution: Starting from real user queries, we generate diverse queries across five popular online shopping domains. (2) Query complexity evolution: We further evolve these queries to increase complexity, considering product attributes, search filters, and sorting preferences, and classify them into three levels: easy, medium, and hard, based on the number of evolutions. (3) Fine-grained and holistic evaluation: We propose an automated evaluation framework that assesses agent performance in terms of fine-grained aspects (product attributes, search filters, and sorting preferences) and reports the overall success rate through holistic evaluation. We conduct a systematic evaluation of retrieval-augmented generation (RAG) methods, web agents, and deep research systems. Results show that RAG struggles with complex queries due to its lack of web interaction, while other methods face significant challenges with filters and sorting preferences, leading to low overall success rates. We also perform cross-category, complexity-based evaluations and error analyses to support the advancement of deep research shopping agents.

## Requirements

```
pip install -r requirements.txt
```

Note that set your api key and base_url in the **.env file**

## Shopping Query Evolution

![framework](./assets/evolution.jpg)

The query evolution pipeline in *DeepShop* is designed to simulate realistic and increasingly complex online shopping behaviors through a two-stage process: query diversity evolution and query complexity evolution. In the first stage, query diversity evolution, the authors start with 50 real-world seed queries from existing benchmarks (Mind2Web-Live and WebVoyager) and expand them using GPT-4o to cover five popular product categories: Books, Electronics, Home, Fashion, and Sports. Each seed query is rewritten to target a different domain, creating a more balanced and representative dataset that captures diverse user intents. In the second stage, query complexity evolution, each diversified query is progressively enhanced across three dimensions—product attributes (e.g., brand, color, size), search filters (e.g., rating thresholds, shipping policies), and sorting preferences (e.g., lowest price, highest rating). These enhancements are applied iteratively in five rounds, with one dimension randomly selected in each iteration, resulting in a set of increasingly complex queries. The final dataset includes queries of varying difficulty levels (easy, medium, and hard), mimicking how real users refine their searches over time. This pipeline is essential for constructing a challenging and realistic benchmark that tests agents’ ability to generalize across domains and handle fine-grained user requirements in dynamic e-commerce environments.

```
sh  ./scripts/run_data_evolution.sh
```

## Fine-grained and Holistic Evaluation

The evaluation pipeline in *DeepShop* is designed to comprehensively assess web agents' ability to handle complex online shopping tasks through a two-stage protocol: fine-grained evaluation and holistic task success evaluation. In the fine-grained evaluation stage, each query is decomposed into three subcomponents—product attributes, search filters, and sorting preferences. Using GPT-4o, each agent's result is automatically assessed against these subqueries by comparing the agent's final outputs and screenshots with the specified requirements, with binary labels ("Success" or "Not Success") assigned for each subgoal. This allows for partial credit and diagnostic insights into failure modes. In the holistic evaluation stage, the system checks whether all applicable subcomponents are satisfied. A query is marked as successful only if the agent correctly fulfills all explicitly stated requirements; omitted components are treated as automatically satisfied.

```
sh ./scripts/run_evaluation.sh
```

Note that we have provided examples in the folder results to make it easier to run the review.