#!/usr/bin/env python3
"""
自動更新所有 Git 專案的所有分支
支援跨平台執行（Windows、macOS、Linux）
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Set, Tuple


class GitRepoUpdater:
    """Git Repository 更新器"""

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

    def update_branch(self, repo_path: Path, branch: str) -> bool:
        """
        更新單一分支

        Args:
            repo_path: Repository 路徑
            branch: 分支名稱

        Returns:
            是否成功
        """
        print(f"    📌 切換到分支: {branch}")

        # Checkout 分支
        success, output = self.run_git_command(repo_path, ["checkout", branch])
        if not success:
            print(f"      ❌ 切換失敗: {output}")
            return False

        # Pull 最新變更
        print(f"    ⬇️  拉取最新變更...")
        success, output = self.run_git_command(repo_path, ["pull"])

        if success:
            if "Already up to date" in output or "Already up-to-date" in output:
                print(f"      ✓ 已是最新")
            else:
                print(f"      ✓ 更新成功")
            return True
        else:
            print(f"      ⚠️  拉取失敗: {output}")
            return False

    def create_tracking_branch(self, repo_path: Path, branch: str) -> bool:
        """
        建立追蹤分支

        Args:
            repo_path: Repository 路徑
            branch: 分支名稱

        Returns:
            是否成功
        """
        print(f"    🌱 建立追蹤分支: {branch}")

        success, output = self.run_git_command(
            repo_path, ["checkout", "-b", branch, f"origin/{branch}"]
        )

        if success:
            print(f"      ✓ 建立成功")
            return True
        else:
            print(f"      ❌ 建立失敗: {output}")
            return False

    def update_repo(self, repo_path: Path, auto_track: bool = False):
        """
        更新單一 Repository

        Args:
            repo_path: Repository 路徑
            auto_track: 是否自動建立遠端追蹤分支
        """
        print(f"\n{'='*80}")
        print(f"📦 處理專案: {repo_path.name}")
        print(f"{'='*80}")

        # 儲存目前分支
        original_branch = self.get_current_branch(repo_path)
        print(f"  ℹ️  目前分支: {original_branch}")

        # Fetch 所有遠端變更
        print(f"  🔄 執行 git fetch --all...")
        success, output = self.run_git_command(repo_path, ["fetch", "--all", "--prune"])

        if not success:
            print(f"  ❌ Fetch 失敗: {output}")
            return

        print(f"  ✓ Fetch 完成")

        # 取得所有分支
        local_branches = self.get_local_branches(repo_path)
        remote_branches = self.get_remote_branches(repo_path)

        print(f"\n  📊 分支統計:")
        print(f"    本地分支: {len(local_branches)} 個")
        print(f"    遠端分支: {len(remote_branches)} 個")

        # 更新所有本地分支
        if local_branches:
            print(f"\n  🔄 更新本地分支...")
            for branch in sorted(local_branches):
                self.update_branch(repo_path, branch)

        # 處理遠端存在但本地不存在的分支
        remote_only = remote_branches - local_branches

        if remote_only:
            print(f"\n  🌐 發現 {len(remote_only)} 個遠端限定分支:")
            for branch in sorted(remote_only):
                print(f"    - {branch}")

            if auto_track:
                print(f"\n  🔄 自動建立追蹤分支...")
                for branch in sorted(remote_only):
                    self.create_tracking_branch(repo_path, branch)
            else:
                # 詢問使用者是否建立追蹤分支
                response = input(f"\n  是否建立這些追蹤分支？(y/n/all): ").lower()

                if response == "all":
                    for branch in sorted(remote_only):
                        self.create_tracking_branch(repo_path, branch)
                elif response == "y":
                    for branch in sorted(remote_only):
                        response = input(f"    建立 {branch}？(y/n): ").lower()
                        if response == "y":
                            self.create_tracking_branch(repo_path, branch)

        # 切回原始分支
        if original_branch:
            print(f"\n  ↩️  切回原始分支: {original_branch}")
            self.run_git_command(repo_path, ["checkout", original_branch])

        print(f"\n  ✅ 專案更新完成")

    def update_all_repos(self, auto_track: bool = False):
        """
        更新所有 Git Repositories

        Args:
            auto_track: 是否自動建立遠端追蹤分支
        """
        repos = self.find_git_repos()

        if not repos:
            print("❌ 未找到任何 Git 專案")
            return

        print(f"\n✓ 共找到 {len(repos)} 個 Git 專案\n")

        for repo in repos:
            try:
                self.update_repo(repo, auto_track)
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
        description="自動更新所有 Git 專案的所有分支",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  %(prog)s                          # 在當前目錄掃描並更新
  %(prog)s /path/to/projects        # 在指定目錄掃描並更新
  %(prog)s --auto-track             # 自動建立所有遠端追蹤分支
  %(prog)s /path/to/projects -a     # 指定目錄並自動建立追蹤分支
        """,
    )

    parser.add_argument(
        "path", nargs="?", default=".", help="要掃描的根目錄路徑（預設為當前目錄）"
    )

    parser.add_argument(
        "-a",
        "--auto-track",
        action="store_true",
        help="自動建立所有遠端追蹤分支（不詢問）",
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

    # 執行更新
    updater = GitRepoUpdater(str(path))
    updater.update_all_repos(auto_track=args.auto_track)


if __name__ == "__main__":
    main()
