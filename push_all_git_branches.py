#!/usr/bin/env python3
"""
自動推送所有 Git 專案的所有本地分支到 origin
支援跨平台執行（Windows、macOS、Linux）
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


class GitRepoPusher:
    """Git Repository 推送器"""

    def __init__(self, root_path: str):
        """
        初始化

        Args:
            root_path: 要掃描的根目錄路徑
        """
        self.root_path = Path(root_path).resolve()

    def find_git_repos(self) -> List[Path]:
        """
        尋找所有 Git 專案

        Returns:
            包含 .git 目錄的專案路徑列表
        """
        git_repos = []

        print(f"🔍 掃描目錄: {self.root_path}")

        for item in self.root_path.iterdir():
            if item.is_dir():
                git_dir = item / ".git"
                if git_dir.exists():
                    git_repos.append(item)
                    print(f"  ✓ 找到 Git 專案: {item.name}")

        return git_repos

    def run_git_command(
        self, repo_path: Path, command: List[str], capture_output: bool = True
    ) -> Tuple[bool, str]:
        """
        執行 Git 命令

        Args:
            repo_path: Repository 路徑
            command: Git 命令列表
            capture_output: 是否捕獲輸出

        Returns:
            (成功與否, 輸出內容)
        """
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=repo_path,
                capture_output=capture_output,
                text=True,
                timeout=300,  # 5 分鐘超時
            )

            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "命令執行超時"
        except Exception as e:
            return False, str(e)

    def get_local_branches(self, repo_path: Path) -> Set[str]:
        """
        取得所有本地分支

        Args:
            repo_path: Repository 路徑

        Returns:
            本地分支名稱集合
        """
        success, output = self.run_git_command(
            repo_path, ["branch", "--format=%(refname:short)"]
        )

        if success:
            branches = set(line.strip() for line in output.split("\n") if line.strip())
            return branches

        return set()

    def get_remote_branches(self, repo_path: Path) -> Set[str]:
        """
        取得所有遠端分支（不含 origin/ 前綴）

        Args:
            repo_path: Repository 路徑

        Returns:
            遠端分支名稱集合
        """
        success, output = self.run_git_command(
            repo_path, ["branch", "-r", "--format=%(refname:short)"]
        )

        if success:
            branches = set()
            for line in output.split("\n"):
                line = line.strip()
                if line and "->" not in line:  # 排除 HEAD -> xxx 這類參照
                    # 移除 origin/ 前綴
                    if line.startswith("origin/"):
                        branch_name = line[7:]  # 移除 "origin/"
                        branches.add(branch_name)
            return branches

        return set()

    def get_current_branch(self, repo_path: Path) -> str:
        """
        取得目前分支名稱

        Args:
            repo_path: Repository 路徑

        Returns:
            目前分支名稱
        """
        success, output = self.run_git_command(repo_path, ["branch", "--show-current"])
        return output if success else ""

    def check_uncommitted_changes(self, repo_path: Path) -> bool:
        """
        檢查是否有未提交的變更

        Args:
            repo_path: Repository 路徑

        Returns:
            是否有未提交的變更
        """
        success, output = self.run_git_command(repo_path, ["status", "--porcelain"])
        return success and bool(output.strip())

    def push_branch(
        self, repo_path: Path, branch: str, force: bool = False, set_upstream: bool = False
    ) -> bool:
        """
        推送單一分支

        Args:
            repo_path: Repository 路徑
            branch: 分支名稱
            force: 是否強制推送
            set_upstream: 是否設定上游分支

        Returns:
            是否成功
        """
        print(f"    📤 推送分支: {branch}")

        # 構建推送命令
        command = ["push"]
        
        if set_upstream:
            command.extend(["--set-upstream", "origin", branch])
        else:
            command.extend(["origin", branch])
        
        if force:
            command.append("--force")

        success, output = self.run_git_command(repo_path, command)

        if success:
            if "Everything up-to-date" in output:
                print(f"      ✓ 已是最新")
            elif "new branch" in output:
                print(f"      ✓ 新分支推送成功")
            else:
                print(f"      ✓ 推送成功")
            return True
        else:
            # 檢查是否需要設定 upstream
            if "has no upstream branch" in output or "set-upstream" in output:
                print(f"      ⚠️  需要設定上游分支，重新嘗試...")
                return self.push_branch(repo_path, branch, force, set_upstream=True)
            else:
                print(f"      ❌ 推送失敗: {output}")
                return False

    def push_repo(
        self,
        repo_path: Path,
        force: bool = False,
        check_changes: bool = True,
        push_all: bool = False,
    ):
        """
        推送單一 Repository

        Args:
            repo_path: Repository 路徑
            force: 是否強制推送
            check_changes: 是否檢查未提交的變更
            push_all: 是否推送所有分支（包括遠端已存在的）
        """
        print(f"\n{'='*80}")
        print(f"📦 處理專案: {repo_path.name}")
        print(f"{'='*80}")

        # 儲存目前分支
        original_branch = self.get_current_branch(repo_path)
        print(f"  ℹ️  目前分支: {original_branch}")

        # 檢查未提交的變更
        if check_changes and self.check_uncommitted_changes(repo_path):
            print(f"  ⚠️  警告: 有未提交的變更")
            response = input(f"  是否繼續推送？(y/n): ").lower()
            if response != "y":
                print(f"  ⏭️  跳過此專案")
                return

        # 先 fetch 取得最新的遠端資訊
        print(f"  🔄 執行 git fetch...")
        success, output = self.run_git_command(repo_path, ["fetch", "--all"])

        if not success:
            print(f"  ❌ Fetch 失敗: {output}")
            print(f"  ⚠️  將繼續推送，但可能與遠端狀態不同步")

        # 取得所有分支
        local_branches = self.get_local_branches(repo_path)
        remote_branches = self.get_remote_branches(repo_path)

        print(f"\n  📊 分支統計:")
        print(f"    本地分支: {len(local_branches)} 個")
        print(f"    遠端分支: {len(remote_branches)} 個")

        if not local_branches:
            print(f"  ⚠️  沒有本地分支可推送")
            return

        # 決定要推送哪些分支
        if push_all:
            branches_to_push = local_branches
            print(f"\n  🔄 推送所有本地分支...")
        else:
            # 只推送遠端不存在的分支
            branches_to_push = local_branches - remote_branches
            
            if branches_to_push:
                print(f"\n  🌱 發現 {len(branches_to_push)} 個本地限定分支:")
                for branch in sorted(branches_to_push):
                    print(f"    - {branch}")
            else:
                print(f"\n  ℹ️  所有本地分支都已存在於遠端")
                
                # 詢問是否要推送現有分支的更新
                response = input(f"  是否推送現有分支的更新？(y/n): ").lower()
                if response == "y":
                    branches_to_push = local_branches
                    print(f"\n  🔄 推送所有分支的更新...")
                else:
                    print(f"  ✅ 專案處理完成")
                    return

        # 推送所有選定的分支
        success_count = 0
        fail_count = 0

        for branch in sorted(branches_to_push):
            # 切換到該分支
            print(f"  📌 切換到分支: {branch}")
            success, output = self.run_git_command(repo_path, ["checkout", branch])
            
            if not success:
                print(f"    ❌ 切換失敗: {output}")
                fail_count += 1
                continue

            # 推送分支
            if self.push_branch(repo_path, branch, force):
                success_count += 1
            else:
                fail_count += 1

        # 切回原始分支
        if original_branch:
            print(f"\n  ↩️  切回原始分支: {original_branch}")
            self.run_git_command(repo_path, ["checkout", original_branch])

        # 顯示統計
        print(f"\n  📊 推送統計:")
        print(f"    成功: {success_count} 個")
        print(f"    失敗: {fail_count} 個")
        print(f"\n  ✅ 專案處理完成")

    def push_all_repos(
        self,
        force: bool = False,
        check_changes: bool = True,
        push_all: bool = False,
    ):
        """
        推送所有 Git Repositories

        Args:
            force: 是否強制推送
            check_changes: 是否檢查未提交的變更
            push_all: 是否推送所有分支
        """
        repos = self.find_git_repos()

        if not repos:
            print("❌ 未找到任何 Git 專案")
            return

        print(f"\n✓ 共找到 {len(repos)} 個 Git 專案\n")

        for repo in repos:
            try:
                self.push_repo(repo, force, check_changes, push_all)
            except KeyboardInterrupt:
                print("\n\n⚠️  使用者中斷操作")
                sys.exit(1)
            except Exception as e:
                print(f"\n❌ 處理專案時發生錯誤: {e}")
                continue

        print(f"\n{'='*80}")
        print(f"🎉 所有專案處理完成！")
        print(f"{'='*80}")


def main():
    """主程式"""
    import argparse

    parser = argparse.ArgumentParser(
        description="自動推送所有 Git 專案的所有本地分支到 origin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  %(prog)s                          # 在當前目錄掃描並推送
  %(prog)s /path/to/projects        # 在指定目錄掃描並推送
  %(prog)s --all                    # 推送所有分支（包括遠端已存在的）
  %(prog)s --force                  # 強制推送
  %(prog)s --no-check               # 不檢查未提交的變更
  %(prog)s /path/to/projects -a -f  # 指定目錄、推送所有分支並強制推送
        """,
    )

    parser.add_argument(
        "path", nargs="?", default=".", help="要掃描的根目錄路徑（預設為當前目錄）"
    )

    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="推送所有分支（包括遠端已存在的）",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="強制推送（警告：可能覆蓋遠端的變更）",
    )

    parser.add_argument(
        "--no-check",
        action="store_true",
        help="不檢查未提交的變更",
    )

    args = parser.parse_args()

    # 檢查路徑是否存在
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"❌ 錯誤: 路徑不存在: {path}")
        sys.exit(1)

    if not path.is_dir():
        print(f"❌ 錯誤: 路徑不是目錄: {path}")
        sys.exit(1)

    # 警告訊息
    if args.force:
        print("⚠️  警告: 您正在使用強制推送模式，這可能會覆蓋遠端的變更！")
        response = input("確定要繼續嗎？(y/n): ").lower()
        if response != "y":
            print("已取消操作")
            sys.exit(0)

    # 執行推送
    pusher = GitRepoPusher(str(path))
    pusher.push_all_repos(
        force=args.force,
        check_changes=not args.no_check,
        push_all=args.all,
    )


if __name__ == "__main__":
    main()
