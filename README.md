# 使用方式

# 將所有 git 專案中，所有分支都 pull 最新的變更

## Windows

```shell
# 在當前目錄掃描並更新
python update_all_git_branches.py

# 在指定目錄掃描並更新
python update_all_git_branches.py "E:\Projects\\"

# 自動建立所有遠端追蹤分支（不詢問）
python update_all_git_branches.py --auto-track

# 查看說明
python update_all_git_branches.py --help
```

## Linux / macOS

```shell
# 在當前目錄掃描並更新
python update_all_git_branches.py

# 在指定目錄掃描並更新
python update_all_git_branches.py "E:\Projects\\"

# 自動建立所有遠端追蹤分支（不詢問）
python update_all_git_branches.py --auto-track

# 查看說明
python update_all_git_branches.py --help
```

# 將本地的 repo 中所有的 branch 推上 origin

## Windows

```shell
# 推送當前目錄下所有專案的新分支
python push_all_git_branches.py

# 推送指定目錄的所有分支
python push_all_git_branches.py "E:\Projects\\" --all

# 強制推送所有分支
python push_all_git_branches.py --all --force
```

## Linux / macOS

```shell
# 推送當前目錄下所有專案的新分支
python push_all_git_branches.py

# 推送指定目錄的所有分支
python push_all_git_branches.py "E:\Projects\\" --all

# 強制推送所有分支
python push_all_git_branches.py --all --force
```
