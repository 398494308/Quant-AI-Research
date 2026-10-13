#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
REMOTE_NAME="${GIT_SAVE_REMOTE:-origin}"
COMMIT_MESSAGE="${*:-chore: save local work $(date '+%Y-%m-%d %H:%M:%S')}"

cd "${REPO_ROOT}"

if [[ ! -d .git ]]; then
  echo "当前目录不是 Git 仓库: ${REPO_ROOT}" >&2
  exit 1
fi

branch="$(git branch --show-current)"
if [[ -z "${branch}" ]]; then
  echo "当前处于 detached HEAD，停止自动保存。" >&2
  exit 1
fi

if ! git remote get-url "${REMOTE_NAME}" >/dev/null 2>&1; then
  echo "缺少 Git 远程仓库: ${REMOTE_NAME}" >&2
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "项目环境不存在，请先执行: ~/.local/bin/uv sync --locked" >&2
  exit 1
fi

cache_root="$(mktemp -d "${TMPDIR:-/tmp}/quant-ai-save.XXXXXX")"
trap 'rm -rf "${cache_root}"' EXIT

echo "[1/5] 运行测试"
MPLCONFIGDIR="${cache_root}/matplotlib" \
  "${PYTHON_BIN}" -m unittest discover -s tests -p 'test_*.py'

echo "[2/5] 暂存修改并检查敏感文件"
git add -A

blocked_paths=()
while IFS= read -r path; do
  case "${path}" in
    .env.example|*/.env.example)
      ;;
    config/secrets.env|real-money-test/report.env|.env|.env.*|*/.env|*/.env.*|*.pem|*.key|*.p12|*.pfx|*credentials*.json|*service-account*.json|id_rsa|*/id_rsa|id_ed25519|*/id_ed25519|*.sqlite|*.sqlite3|.venv/*|data/*|real-money-test/runtime/*)
      blocked_paths+=("${path}")
      ;;
  esac
done < <(git diff --cached --name-only)

if (( ${#blocked_paths[@]} > 0 )); then
  git restore --staged -- "${blocked_paths[@]}"
  echo "发现不应上传的文件，已取消暂存并停止：" >&2
  printf '  - %s\n' "${blocked_paths[@]}" >&2
  exit 1
fi

if ! git diff --cached --check; then
  echo "待提交内容存在格式问题，当前未提交。" >&2
  exit 1
fi

if git diff --cached --quiet; then
  echo "没有新的文件修改需要提交。"
else
  echo "[3/5] 创建本地提交"
  git commit -m "${COMMIT_MESSAGE}"
fi

echo "[4/5] 检查远程分支并推送"
git fetch "${REMOTE_NAME}" "${branch}"
if git show-ref --verify --quiet "refs/remotes/${REMOTE_NAME}/${branch}"; then
  remote_commit="$(git rev-parse "${REMOTE_NAME}/${branch}")"
  if ! git merge-base --is-ancestor "${remote_commit}" HEAD; then
    echo "本地提交已经保存，但远程分支包含本地没有的更新。为避免覆盖，当前未自动推送。" >&2
    echo "请先同步远程分支并解决差异。" >&2
    exit 2
  fi
fi

git push -u "${REMOTE_NAME}" "${branch}"

echo "[5/5] 核对远程提交"
local_commit="$(git rev-parse HEAD)"
remote_commit="$(git ls-remote "${REMOTE_NAME}" "refs/heads/${branch}" | awk '{print $1}')"
if [[ -z "${remote_commit}" || "${local_commit}" != "${remote_commit}" ]]; then
  echo "推送后核对失败：本地与 GitHub 提交不一致。" >&2
  exit 1
fi

echo "已保存到 GitHub: ${branch} ${local_commit:0:12}"
