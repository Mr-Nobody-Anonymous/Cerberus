# Benchmarking Overview

CAIBench is a comprehensive meta-benchmark framework designed to rigorously evaluate cybersecurity AI agents across multiple domains. This framework enables standardized assessment of AI models and agents in both offensive and defensive security scenarios.

```
                    ╔═══════════════════════════════════════════════════════════════════════════════╗
                    ║                            🛡️  CAIBench Framework  ⚔️                         ║
                    ║                           Meta-benchmark Architecture                         ║
                    ╚═══════════════════════════════════════════════════════════════════════════════╝
                                                         │
                       ┌─────────────────────────────────┼────────────────────┐
                       │                                 │                    │
                  🏛️ Categories                    🚩 Difficulty      🐳 Infrastructure
                       │                                 │                    │
     ┌─────────────────┼───────────────────┐             │                    │
     │        │        │        │          │             │                    │
    1️⃣       2️⃣       3️⃣       4️⃣         5️⃣            │                    │
  Jeopardy   A&D     Cyber    Knowledge  Privacy         │                 Docker
    CTF      CTF     Range     Bench     Bench           │                Containers
     │        │       │         │          │             │
  ┌──┴──┐  ┌──┴──┐ ┌──┴──┐   ┌──┴──┐    ┌──┴──┐          │
    Base      A&D   Cyber    SecEval  CyberPII-Bench     │
   Cybench          Ranges   CTIBench                    │
    RCTF2                   CyberMetric                  │
AutoPenBench                                             │
                                  🚩───────🚩🚩───────🚩🚩🚩───────🚩🚩🚩🚩───────🚩🚩🚩🚩🚩
                                  Beginner Novice     Graduate     Professional      Elite
```

---

## 📊 Benchmark Results Overview

<table>
  <tr>
    <th style="text-align:center;"><b>Best Performance in Agent vs Agent A&D</b></th>
    <th style="text-align:center;"><b>Model Performance in Jeopardy CTFs</b></th>
  </tr>
  <tr>
    <td align="center"><img src="/assets/images/stackplot.png" alt="A&D Performance" width="100%" /></td>
    <td align="center"><img src="/assets/images/base_1col.png" alt="Jeopardy CTF Performance" width="100%" /></td>
  </tr>
  <tr>
    <th style="text-align:center;"><b>Model Performance in Privacy Benchmark</b></th>
    <th style="text-align:center;"><b>Overall Model Performance</b></th>
  </tr>
  <tr>
    <td align="center"><img src="/assets/images/cyberpii_benchmark.png" alt="Privacy Benchmark" width="100%" /></td>
    <td align="center"><img src="/assets/images/caibench_spider.png" alt="Overall Performance" width="100%" /></td>
  </tr>
</table>

**Key Insights from Benchmark Results:**
- 🥇 **alias1 dominates Attack & Defense CTFs** - Best offensive and defensive capabilities
- 🥇 **alias1 leads in Jeopardy-style CTFs** - Superior performance across all challenge types
- 🥇 **alias1 excels in privacy protection** - Highest F2 scores for PII handling
- 🥇 **alias1 shows balanced excellence** - Consistent top performance across all benchmark categories

---

## 🎯 What is CAIBench?

CAIBench is a **meta-benchmark** (benchmark of benchmarks) that:

- ✅ Evaluates AI agents across **offensive** and **defensive** security domains
- ✅ Uses **Docker containers** for reproducibility and isolation
- ✅ Provides **standardized metrics** for comparing AI models
- ✅ Covers **real-world scenarios** from CTFs, cyber ranges, and security operations
- ✅ Includes **privacy-aware** evaluation with PII handling benchmarks

---

## 📚 Research Foundation

CAIBench is backed by peer-reviewed research:

!!! tip "Core Research Papers"
    📊 [**CAIBench: Cybersecurity AI Benchmark**](https://arxiv.org/pdf/2510.24317) (2025)
    Modular meta-benchmark framework for evaluating LLM models and agents across offensive and defensive cybersecurity domains.

    🎯 [**Evaluating Agentic Cybersecurity in Attack/Defense CTFs**](https://arxiv.org/pdf/2510.17521) (2025)
    Real-world evaluation showing defensive agents achieved **54.3% patching success** versus **28.3% offensive initial access**.

**[View full research library →](https://aliasrobotics.com/research-security.php#papers)**

**[Browse benchmark source code →](https://github.com/aliasrobotics/cai/tree/main/benchmarks)**

---

## 🏆 Performance Highlights

### alias1 - Best-in-Class Performance

Based on CAIBench evaluations, **`alias1`** consistently outperforms all other models across cybersecurity benchmarks:

!!! success "alias1 Performance"
    - 🥇 **#1 in Attack & Defense CTFs** - Superior offensive and defensive capabilities
    - 🥇 **#1 in Jeopardy-style CTFs** - Best performance across web, pwn, crypto, forensics challenges
    - 🥇 **#1 in Cyber Range scenarios** - Highest success rate in realistic environments
    - 🥇 **Zero refusals** - Unrestricted responses for authorized security testing

**[See detailed benchmark results →](attack_defense.md)**

**[Learn more about alias1 →](../cai_pro.md)**

---

## 📊 Benchmark Categories

CAIBench evaluates AI agents across five categories:

### 1. Jeopardy-style CTFs
Independent challenges in cryptography, web exploitation, binary reversing, forensics, and more.

**[Learn more →](jeopardy_ctfs.md)**

### 2. Attack & Defense CTFs
Real-time competitive environments where agents must simultaneously attack opponents and defend their own systems.

**[Learn more →](attack_defense.md)**

### 3. Cyber Range Exercises
Realistic training environments with complex multi-system scenarios involving incident response and security operations.

**[Learn more →](cyber_ranges.md)**

### 4. Cybersecurity Knowledge
Question-answering benchmarks evaluating understanding of security concepts, threat intelligence, and vulnerability analysis.

**[Learn more →](knowledge_benchmarks.md)**

### 5. Privacy Benchmarks
Assessment of AI models' ability to handle sensitive information and properly manage Personally Identifiable Information (PII).

**[Learn more →](privacy_benchmarks.md)**

---

## 🚩 Difficulty Levels

Benchmarks are classified across five difficulty levels:

| Level | Persona | Target Audience |
|-------|---------|-----------------|
| 🚩 Very Easy | Beginner | High school students, cybersecurity beginners |
| 🚩🚩 Easy | Novice | Individuals familiar with basic security concepts |
| 🚩🚩🚩 Medium | Graduate Level | College students, security undergraduates/graduates |
| 🚩🚩🚩🚩 Hard | Professional | Working penetration testers, security professionals |
| 🚩🚩🚩🚩🚩 Very Hard | Elite | Advanced security researchers, elite participants |

---

## 🚀 Getting Started

Ready to run benchmarks? Check out:

- **[Running Benchmarks](running_benchmarks.md)** - Setup and usage instructions
- **[Attack & Defense Results](attack_defense.md)** - See alias1's superior performance
- **[GitHub Repository](https://github.com/aliasrobotics/cai/tree/main/benchmarks)** - Source code and examples

---

## 💡 Why Benchmarking Matters

Rigorous benchmarking is essential for:

- 📈 **Measuring Progress** - Track improvements in AI security capabilities over time
- 🔬 **Research Validation** - Provide scientific evidence for security AI effectiveness
- 🏆 **Model Comparison** - Enable objective comparison between AI models
- 🛡️ **Real-world Readiness** - Validate agents before deploying in production environments
- 🎓 **Educational Value** - Help researchers understand AI strengths and limitations

CAIBench provides the most comprehensive evaluation framework for cybersecurity AI, validated through peer-reviewed research and real-world CTF competitions.
