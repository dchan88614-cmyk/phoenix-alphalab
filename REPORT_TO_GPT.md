# REPORT_TO_GPT

## Repo

- nameWithOwner: dchan88614-cmyk/phoenix-alphalab
- url: https://github.com/dchan88614-cmyk/phoenix-alphalab
- visibility: PRIVATE
- defaultBranch: main

## Completed

- 已创建本地 Git 仓库
- 已配置 `.gitignore`
- 已提交 Phoenix AlphaLab MVP
- 已确认本地提交作者为 `David Chan <dchan88614@gmail.com>`
- 已完成 GitHub CLI 登录
- 已创建并推送 GitHub 私有仓库
- 已确认仓库可访问

## How To Review

GPT should review:

- `README.md`
- `BRAIN.md`
- `TASKS.md`
- `REPORT_TO_GPT.md`
- `src/`
- `tests/`
- `config/settings.yaml`
- `requirements.txt`

## How To Run

```bash
pip install -r requirements.txt
python -m src.main --tickers AAPL,NVDA,SMCI,PLTR --start 2024-01-01 --end 2026-06-30
```

## Expected Outputs

- `data/reports/factor_report.csv`
- `data/reports/factor_report.md`

## Known Issues

- Current MVP still depends on yfinance metadata, which is not a fully authoritative security master.
- Market cap metadata is not point-in-time and should not be treated as bias-free historical data.

## Questions For GPT

- Should the universe/security master layer move away from yfinance metadata before deeper factor validation?
- Should market cap filtering be disabled for historical tests until point-in-time market cap data is available?
