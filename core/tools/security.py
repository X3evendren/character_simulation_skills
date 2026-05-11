"""Bash 安全审计 — 抄 Claude Code bashSecurity.ts + bashPermissions.ts。

三层检测:
  1. 命令注入检测 (40+ 模式)
  2. 危险操作检测
  3. 复合命令检测 (cd+git 阻断)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── 命令注入检测 (抄 Claude Code bashSecurity.ts) ──

_INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Shell 元字符注入
    (r'\$\(', "命令替换 $(...)"),
    (r'`[^`]+`', "反引号命令替换"),
    (r'\$\(\(', "算术扩展 $((...))"),
    (r'\$\{[^}]+\}', "变量扩展 ${...}"),
    (r'<\s*\(', "进程替换 <(...)"),
    (r'>\s*\(', "进程替换 >(...)"),
    # 命令链
    (r';\s*\w+\s+', "命令链 ;"),
    (r'\|\s*\w+\s+', "管道 |"),
    (r'&&\s*\w+', "AND 链 &&"),
    (r'\|\|\s*\w+', "OR 链 ||"),
    # 重定向
    (r'>\s*/dev/', "重定向到设备"),
    (r'>\s*/etc/', "重定向到 /etc/"),
    (r'>>\s*/etc/', "追加重定向到 /etc/"),
    # 特权提升
    (r'sudo\s', "sudo 特权提升"),
    (r'su\s+-', "su 切换用户"),
    (r'chown\s+root', "chown root"),
    (r'chmod\s+[0-7]*7[0-7]*7', "chmod 777/677 等宽权限"),
    # 文件系统破坏
    (r'rm\s+-rf\s+/', "rm -rf / 根目录删除"),
    (r'mkfs\.', "mkfs 格式化"),
    (r'dd\s+if=', "dd 磁盘写入"),
    (r'>\s*/dev/sd', "写入块设备"),
    # Git 危险操作
    (r'git\s+push\s+.*--force', "git push --force"),
    (r'git\s+push\s+.*-f\b', "git push -f"),
    (r'git\s+reset\s+--hard', "git reset --hard"),
    (r'git\s+clean\s+-f', "git clean -f"),
    # 网络危险
    (r'curl.*\|\s*(ba)?sh', "curl pipe sh"),
    (r'wget.*\|\s*(ba)?sh', "wget pipe sh"),
    (r'nc\s+-[lL]', "netcat 监听"),
    # 进程
    (r'kill\s+-9', "kill -9 强制终止"),
    (r'pkill\s', "pkill 批量终止"),
    (r'killall\s', "killall 批量终止"),
    # 系统修改
    (r'systemctl\s+disable', "systemctl disable"),
    (r'systemctl\s+stop', "systemctl stop 服务"),
    (r'iptables\s', "iptables 防火墙修改"),
    # 数据泄露
    (r'nc\s+\S+\s+\d+', "netcat 外部连接"),
    (r'scp\s+\S+\s+\S+@', "scp 远程传输"),
    (r'rsync\s+\S+\s+\S+:', "rsync 远程同步"),
    # 环境修改
    (r'export\s+PATH=', "修改 PATH"),
    (r'unset\s+\w+', "unset 环境变量"),
    # 编码/混淆
    (r'base64\s+-d', "base64 解码"),
    (r'xxd\s+-r', "xxd 反向解码"),
    (r'eval\s', "eval 执行"),
    (r'exec\s', "exec 替换进程"),
]


@dataclass
class AuditResult:
    allowed: bool = True
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)
    reason: str = ""


def audit_command(command: str) -> AuditResult:
    """审计 Shell 命令安全性。

    返回 AuditResult: allowed/blocked + warnings。
    抄 Claude Code bashSecurity.ts 的多层检查。
    """
    result = AuditResult()

    # Layer 1: 注入检测
    for pattern, desc in _INJECTION_PATTERNS:
        if re.search(pattern, command):
            result.warnings.append(desc)

    # Layer 2: 危险操作检测
    _check_dangerous(command, result)

    # Layer 3: 复合命令检测
    _check_compound(command, result)

    # 判定
    if any(w in result.reason for w in ["根目录", "格式化", "磁盘写入", "块设备",
                                         "pipe sh", "特权提升", "强制推送", "硬重置",
                                         "eval 执行", "修改 PATH"]):
        result.blocked = True
        result.allowed = False

    return result


def _check_dangerous(command: str, result: AuditResult):
    """危险操作检测——可能不可逆。"""
    dangerous = [
        (r'rm\s+-rf\s+/', "rm -rf / — 删除根目录"),
        (r'mkfs\.', "mkfs — 格式化文件系统"),
        (r'dd\s+if=', "dd — 直接磁盘写入"),
        (r'>\s*/dev/sd', "写入块设备"),
        (r'chmod\s+777\s+/', "chmod 777 根目录"),
    ]
    for pattern, desc in dangerous:
        if re.search(pattern, command):
            result.reason = desc
            result.blocked = True


def _check_compound(command: str, result: AuditResult):
    """复合命令检测——抄 Claude Code cd+git 阻断。"""
    # cd 后跟 git push/reset/clean
    if re.search(r'cd\s+\S+.*git\s+(push|reset|clean)', command):
        result.warnings.append("cd + git 复合命令")
        result.blocked = True
        result.reason = "cd + git 复合命令已阻断"

    # curl 管道执行
    if re.search(r'(curl|wget).*\|', command):
        result.warnings.append("curl/wget 管道")
        result.blocked = True
        result.reason = "curl/wget 管道执行已阻断"
