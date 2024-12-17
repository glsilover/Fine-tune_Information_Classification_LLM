# -*- coding: utf-8 -*-

import jieba
import jieba.analyse


def sentences_filter(sentences_content, keywords_topK=20, sentences_topK=10, filtered_sentences_max_num=6, max_chars=500):
    # ---------------------------
    # 步骤1：分词预处理
    # ---------------------------
    # jieba分词可根据需求启用自定义词典（该字典仅能保证正确被分词）
    jieba.load_userdict("datacleaning/High-frequency-vocabulary-jieba.txt")
    # 对文本进行基础清洗（如去除多余空格、换行符等）
    cleaned_text = sentences_content.strip().replace('\n', '').replace('\r', '')
    # print(len(cleaned_text))
    # print(jieba.lcut(cleaned_text))

    # ---------------------------
    # 步骤2：关键词提取（TF-IDF）
    # ---------------------------
    # 参数topK可根据文本长度和需求适当调整，如关键词过少信息不够，过多会冗余

    jieba.analyse.set_idf_path("datacleaning/High-frequency-vocabulary-IDF.txt")
    top_keywords = jieba.analyse.extract_tags(cleaned_text, topK=keywords_topK, withWeight=False)

    # ---------------------------
    # 步骤3：核心句子提取（TextRank）
    # ---------------------------
    # TextRank同样可用于提取关键词或关键句子，这里使用 textrank 提取关键句子
    # topK可根据长度调优，一般选取5~10句即可
    key_sentences = jieba.analyse.textrank(cleaned_text, topK=sentences_topK, withWeight=False, allowPOS=('ns', 'n', 'vn', 'v', 'nr', 'nt', 'nz', 'a', 'd'))

    # 注意：jieba的textrank默认用于关键词提取，如需句子提取，可自行对原文分句后调用textrank关键词后再映射回句子，或使用其他句子抽取工具。
    # 这里给出一个简单的句子抽取方法，如果textrank未直接支持对句子抽取，可手动实现。

    # 简单的句子分句函数（可根据标点适当扩展）
    def split_sentences(text):
        import re
        # 中文分句标点符号列表可根据实际情况微调
        sentences = re.split(r'[。！？!?]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    sent_list = split_sentences(cleaned_text)
    # print(sent_list)

    # 我们使用 textrank 提取关键词后，再在句子列表中根据关键词分数简单选句
    # 另一种方法是直接使用jieba.analyse.textrank_for_keywords计算关键词后，
    # 将关键词与句子匹配，根据句子含关键词权重累加来选出关键句子。
    # 为了清晰起见，这里示例使用关键词匹配权重法手动实现。

    keyword_weights = {k: i for i, k in enumerate(top_keywords[::-1], start=1)}
    # 上面将关键词反向排序，以最高权重为最大值

    # print(keyword_weights)

    # --------------------------------------
    # 定义领域相关关键词词典(根据标签类别定制)
    # 假设需要重点聚焦这些类别相关的文本:
    domain_keywords = [
        "计算机", "云计算", "人工智能", "架构师", "经济观察", "商业案例",
        "汽车行业", "个人娱乐", "芯片", "CPU", "GPU",
        "经济", "商业", "英伟达", "计算", "存储", "网络", "AI", "算力"
    ]


    # --------------------------------------
    # 启发式过滤: 保留与任务领域相关的句子
    # 策略：句子分词后，如包含任一domain_keywords_set中关键词则保留
    
    # 根据关键词权重对句子进行打分排序
    def sentence_rank(sentences_list, keyword_weights):
        """
        :param sentences_list: 待排序句子的列表
        :param keyword_weights: 关键词权重计算函数
        :return: 按得分排序的句子列表
        """
        def sentence_score(sent):
                words = jieba.lcut(sent)
                score = sum(keyword_weights.get(w, 0) for w in words)
                return score
    
        # 对句子进行评分并排序
        scored_sentences = [(s, sentence_score(s)) for s in sentences_list]
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored_sentences]


    # 根据领域关键词筛选句子并按优先级排序，保证至少返回N个句子
    def filter_and_rank_sentences(sent_list, keyword_weights, domain_keywords, N=6):
        """
        :param sent_list: 所有句子的列表
        :param keyword_weights: 关键词权重计算函数
        :param domain_keywords: 领域相关关键词列表
        :param N: 返回的句子数量
        :return: 筛选并排序后的句子列表
        """
        # 转换领域关键词为集合
        domain_keywords_set = set(domain_keywords)
    
        # 过滤包含领域关键词的句子
        filtered_sentences = [
            s for s in sent_list
            if any(w in domain_keywords_set for w in jieba.lcut(s))
        ]
    
        # 对过滤的句子进行排序
        ranked_filtered_sentences = sentence_rank(filtered_sentences, keyword_weights)
    
        # 如果不足N个句子，从所有句子中补充
        if len(ranked_filtered_sentences) < N:
            # 对所有句子排序
            ranked_all_sentences = sentence_rank(sent_list, keyword_weights)
            # 补充缺失的句子
            additional_needed = N - len(ranked_filtered_sentences)
            additional_sentences = [
                s for s in ranked_all_sentences if s not in ranked_filtered_sentences
            ][:additional_needed]
            ranked_filtered_sentences.extend(additional_sentences)
    
        # 返回最终的N个句子
        return ranked_filtered_sentences[:N]



    # 运行筛选和排序
    result_sentences = filter_and_rank_sentences(sent_list, keyword_weights, domain_keywords, N=6)


    # print(selected_sentences)

    # ---------------------------
    # 步骤4：合并关键词与精简句子
    # ---------------------------
    final_text = "关键词: " + " ".join(top_keywords) + "\n" + "核心句子:\n" + "\n".join(result_sentences)
    # print(final_text)

    # ---------------------------
    # 步骤5：对final_text进行长度控制（可选）
    # ---------------------------
    # 假设此时final_text仍过长，您可以对字符长度进行截断
    MAX_CHARS = max_chars  # 假设我们希望不超过500个字符
    if len(final_text) > MAX_CHARS:
        final_text = final_text[:MAX_CHARS] + "..."

    # print("最终处理后的文本片段：\n", final_text)

    return final_text
