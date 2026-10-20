<div align="center">
<img src="assets/social-preview.png" alt="permission-gate" width="860">
</div>

<h1 align="center">permission-gate</h1>

<p align="center"><b>Score how much more your agent can do than it should.</b><br><sub>one file · zero dependencies · stdlib only</sub></p>

<p align="center"><a href="https://github.com/chenhz01/permission-gate/actions/workflows/gate.yml"><img src="https://github.com/chenhz01/permission-gate/actions/workflows/gate.yml/badge.svg" alt="tests"></a> <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square" alt="python"> <img src="https://img.shields.io/badge/dependencies-0-2ea44f?style=flat-square" alt="deps"> <img src="https://img.shields.io/badge/license-Apache--2.0%20%2B%20CC%20BY%204.0-blue?style=flat-square" alt="license"></p>

---

## The failure this catches

- An agent that only answers doc questions holds write_file, shell, and outbound network.
- Nobody audited the tool list; three months later six high-risk ops had quietly appeared.
- Security asks for the agent's least-privilege scope and the answer is 'roughly these'.

One command, on a file you already have:

```bash
python gate.py audit --manifest examples/tools.json --policy examples/policy.json --min-score 80
```

<details>
<summary><b>Real output</b> — produced by the bundled <code>examples/</code>, not a mock-up</summary>

```text
permission-gate report
  pairs: 9  allowed: 2  denied: 1  unreviewed: 6
  surface: 66.7%  risk-weighted: 80.0%  score: 20.0  grade: D
  - decide: allow or deny 'shell:exec' (weight 4)
  - decide: allow or deny 'fs:write' (weight 3)
  - decide: allow or deny 'http:network' (weight 3)
  - decide: allow or deny 'mail:send' (weight 2)
  - decide: allow or deny 'db:query' (weight 2)
```

</details>

## What it does

- Computes an over-permission score from two static files: tool manifest and policy.
- Flags each gap with severity, so you can fix the HIGH ones today.
- Runs in CI as a gate — permission drift fails the build instead of the audit.

## What it does **not** do

- It does not observe runtime calls; a perfectly scoped policy can still be abused.
- It does not know your business role semantics — you declare what the role needs.
- It is not a sandbox. Pair it with one.

Being explicit here is cheaper than a wrong expectation later.

## Exit codes

`0` = a report was produced. `1` = score below `--min-score`. `2` = bad input. **Without `--min-score` this command never fails — it measures, it does not judge.**

## Install

```bash
git clone https://github.com/chenhz01/permission-gate
cd permission-gate
python gate.py --help
```

Python 3.9+. Nothing to `pip install` — stdlib only.

## Use it in CI

```yaml
- name: permission-gate
  run: python gate.py audit --manifest examples/tools.json --policy examples/policy.json --min-score 80
```

## Use it as a GitHub Action

`action.yml` is included, so you can call this repo directly as a composite action.

```yaml
# .github/workflows/gates.yml
- uses: actions/checkout@v4

- uses: chenhz01/permission-gate@v0.1.3
  with:
    # IMPORTANT: this path is inside YOUR repository.
    # The examples/ in this repo are NOT in your workspace — pass your own files.
    args: "audit --manifest path/to/tools.json --policy path/to/policy.json --min-score 80"
```

Pin the tag (`@v0.1.3`) rather than `@main` — `main` moves.
Check [Releases](https://github.com/chenhz01/permission-gate/releases) for the newest tag; `v0.1.0` predates the
fix that makes a mistyped path fail instead of silently passing.

If you omit `args`, the action only prints help and exits 0. It raises a warning
annotation — quoting this gate's own correct usage — so a green check is never
mistaken for "it inspected my files".


## 中文速览

**权限门** — 量化 Agent「能做的事」比「该做的事」多出多少。

- 一个只负责查文档的 Agent，手里握着 write_file、shell 和网络出口。
- 工具清单没人审，三个月后多了 6 个高危操作，没人记得是谁加的。
- 安全评审问「这个 Agent 最小权限是什么」，你只能回答「大概这些吧」。

一行命令：`python gate.py audit --manifest examples/tools.json --policy examples/policy.json --min-score 80`

边界：It does not observe runtime calls; a perfectly scoped policy can still be abused.

### 互推：只装一个的话，装哪个

十五个链接是迷宫，一个症状是门。按上表挑一个，其余九个在下面 [The gates](#the-gates)。
每个仓都能单独活：复制 `gate.py`，一条命令跑完，不共享运行时、不装包、不加配置。
有星就给这一个，没有也不影响任何仓的可用性——没有任何门是「先给星才能用」。

### 热门前置：保证结构，不保证排名

本页承诺的是 **15 项可机器复核的结构特征**，当前 **15/15**（2026-10-20 复核）。
GitHub 从未公开 Trending 的排序算法，所以任何「保证上热门」的说法都在描述一件它不可能知道的事；
本仓不这么说。跑 `python hotness.py` 可自行复算每一条。

## Start here (if you install only one)

Fifteen links is a maze; one symptom is a door. Find your symptom, install that gate,
ignore the rest until it hurts.

| what you are seeing | install this |
|---|---|
| the bill is 10x normal and the trace is a wall of the same step | **[loop-gate](https://github.com/chenhz01/loop-gate)** |
| the agent can delete prod and nobody signed off on that | **permission-gate** ← you are here |
| answers get worse after truncation and nobody knows what got dropped | **[context-gate](https://github.com/chenhz01/context-gate)** |
| two rules in the prompt contradict each other; the model obeys neither | **[instruction-gate](https://github.com/chenhz01/instruction-gate)** |
| AI text ships with fabricated links and empty phrases | **[output-gate](https://github.com/chenhz01/output-gate)** |
| half the repo might be dead and nobody can prove which half | **[deadcode-gate](https://github.com/chenhz01/deadcode-gate)** |

A gate you did not need is a gate you uninstall, so nothing here says "install all
fifteen". Each repo stands alone: copy `gate.py`, run one command, no shared runtime,
no package manager, no config file to grow.

**On stars.** If this one saved you an incident, star it — that is the only signal I get
about which gate to build next. There is no exchange: starring one repo does not owe me
a star on another, and no gate here is unlocked by a star. Star trading breaks GitHub's
rules and would poison the single honest metric this project has.

## Hot-ready guarantee

What is guaranteed is **structure**, not ranking. Fifteen properties, each one
machine-checked against this repo — current score **15/15** (2026-10-20).

Plain version: instead of asking you to trust a badge, I list what I actually checked,
name the script that checks it, and let you re-run it. If one of these lines is false,
that is a bug in my repo, not a matter of taste.

- Falsifiable side: `python hotness.py` re-runs every check and prints the evidence line
  for each one. You do not have to trust this paragraph.
- Non-falsifiable side: GitHub has never published how Trending sorts repositories, so
  any repo promising you a guaranteed spot is telling you something it cannot know.
  This one does not make that promise.
- If a claim on this page stops being true, that is a bug: open an issue and it gets
  fixed in the same week, not in the next launch.

What actually carries this repo:

- the command in this README is byte-for-byte the command CI runs <sub>(89-char argv, exact match)</sub>
- the output block is a real run of `examples/`, not a mock-up <sub>(Real output section)</sub>
- CI asserts the exit code, so the badge can turn red — and it has <sub>(asserts exit=1)</sub>
- every fixture is committed, so a fresh clone reproduces the output <sub>(2 files under examples/ tracked in git)</sub>
- `* -text` in `.gitattributes`: same bytes on Windows and Linux <sub>(.gitattributes * -text)</sub>

## The gates

| # | gate | what it stops |
|---|---|---|
| 02 | **[loop-gate](https://github.com/chenhz01/loop-gate)** | Find where your agent looped, before it burns another run |
| 03 | **permission-gate** ← you are here | Score how much more your agent can do than it should |
| 04 | **[context-gate](https://github.com/chenhz01/context-gate)** | Measure what truncation deletes, before the model starts guessing |
| 05 | **[instruction-gate](https://github.com/chenhz01/instruction-gate)** | Two of your instructions contradict each other. This finds them |
| 06 | **[output-gate](https://github.com/chenhz01/output-gate)** | Before AI-written text ships, run the four checks it always fails |
| 07 | **[memory-expiry-gate](https://github.com/chenhz01/memory-expiry-gate)** | Give every memory a TTL, then prove the expiry semantics actually hold |
| 08 | **[drift-gate](https://github.com/chenhz01/drift-gate)** | When embeddings drift, retrieval quietly rots. Fingerprint it |
| 09 | **[price-gate](https://github.com/chenhz01/price-gate)** | Your cost model is only as good as the price table under it |
| 10 | **[complexity-ceiling](https://github.com/chenhz01/complexity-ceiling)** | Per-file complexity budgets that fail the build instead of the reviewer |
| 11 | **[deadcode-gate](https://github.com/chenhz01/deadcode-gate)** | Quantify how much of the repo is dead, instead of guessing |
| 12 | **[docrot-gate](https://github.com/chenhz01/docrot-gate)** | Docs don't die at once. They rot one stale command at a time |
| 13 | **[leak-gate](https://github.com/chenhz01/leak-gate)** | Scan for internal detail before the doc leaves the building |
| 14 | **[backup-gate](https://github.com/chenhz01/backup-gate)** | A backup you have never verified is a rumor |
| 15 | **[trail-gate](https://github.com/chenhz01/trail-gate)** | Hash-chained agent audit trail — and it verifies its own chain |

## License

- Code: **Apache-2.0** — see [LICENSE](LICENSE)
- Docs and example data: **CC BY 4.0** — see [LICENSE-SPEC](LICENSE-SPEC)

Attribution required when you redistribute the documentation; code can be used commercially
without a separate agreement. See [NOTICE](NOTICE).
