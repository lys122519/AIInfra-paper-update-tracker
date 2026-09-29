# GPU 集群与 AI Infrastructure 检索词设计

本文档说明 `config.yaml` 中检索词的覆盖范围。DBLP 主要按标题检索，因此关键词应使用论文标题中常见、可辨识的技术表达，避免仅使用 `system`、`performance`、`network` 等高噪声单词。

## 检索主题

| 层次 | 检索词 | 主要覆盖内容 |
|---|---|---|
| GPU 集群 | `GPU cluster` | 集群设计、扩展、故障与管理 |
| 资源管理 | `GPU schedul` | GPU scheduler、scheduling 与任务放置 |
| 资源管理 | `GPU resource` | 共享、隔离、弹性与利用率 |
| 加速器集群 | `accelerator cluster` | 异构加速器与大规模部署 |
| AI Infra | `AI infrastructure` | 直接以 AI 基础设施命名的工作 |
| ML 系统 | `ML system` | 机器学习系统设计与优化 |
| 训练 | `distributed training` | 多机多卡训练系统 |
| 训练 | `parallel training` | 训练并行与运行时优化 |
| 推理 | `LLM inference` | 大模型推理架构与性能 |
| 推理 | `model serving` | 在线模型服务与调度 |
| 推理 | `inference serving` | 推理服务系统与性能优化 |
| 网络 | `collective communication` | AllReduce、集合通信库与拓扑优化 |
| 网络 | `RDMA` | 远程直接内存访问与高速互连 |
| 编排 | `Kubernetes` | AI 工作负载的容器编排与资源管理 |
| 并行 | `tensor parallel` | 张量并行、通信与执行计划 |
| 并行 | `pipeline parallel` | 流水线并行、切分与调度 |

`schedul` 有意使用词干形式，以匹配 `schedule`、`scheduler` 和 `scheduling`。每个多词主题保持为独立查询，不合并为复杂 OR 表达式，避免 DBLP 对低频多词分支的召回不稳定。

## Venue 选择原则

- MLSys、NeurIPS、ICML、ICLR：训练、推理和 ML 系统
- OSDI、SOSP、EuroSys、USENIX ATC、SoCC、Middleware：操作系统、云平台、调度和 Kubernetes
- NSDI、SIGCOMM：数据中心网络、RDMA 和集合通信
- SC、HPDC：GPU 集群与高性能计算
- ASPLOS、ISCA、MICRO、HPCA：加速器、内存与体系结构
- TOCS、TPDS：系统与并行分布式计算期刊

## 调整建议

- 噪声过高时，优先缩小 venue，而不是把关键词改成过长的短语。
- 发现典型漏检论文时，从其标题提取稳定术语并新增独立关键词。
- AI Infra 包含多个并列主题，定时任务应进行完整的 `关键词 × venue` 扫描，不应启用 `--primary_only`。
- DBLP 只覆盖书目信息；若希望跟踪 arXiv 最新预印本，需要另行增加 arXiv 数据源。
