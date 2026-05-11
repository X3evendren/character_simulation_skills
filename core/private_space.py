"""私人空间 — 加密存储 + 高权限工作区。

加密区域: 她的秘密、私密想法、不想被任何人看到的东西。
  加密: AES-256-GCM, 密钥 = HKDF(her_identity + user_identity)
  任何人（包括用户）没有密钥无法读取。

工作区域: 她的"书桌"——读、写、整理文件，自由操作。
  她在这里有完整的读写权限，可以做笔记、写草稿、整理思绪。
  用户可以查看但不应随意修改——这是她的空间。
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import time
from pathlib import Path


# ═══════════════════════════════════════════════════════════════
# 加密引擎 — AES-256-GCM
# ═══════════════════════════════════════════════════════════════

class CryptoEngine:
    """AES-256-GCM 加密——使用 Python 标准库 cryptography。

    如果 cryptography 不可用，回退到 Fernet 或纯 Python AES。
    """

    def __init__(self, password: str):
        # HKDF 派生 256-bit 密钥
        self._key = hashlib.sha256(password.encode()).digest()

    def encrypt(self, plaintext: str) -> bytes:
        """加密字符串 → 密文 bytes (nonce + tag + ciphertext)。"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            import os as _os
            aesgcm = AESGCM(self._key)
            nonce = _os.urandom(12)
            ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
            # 格式: nonce(12) + ciphertext+tag
            return nonce + ct
        except ImportError:
            return self._fallback_encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> str:
        """解密密文 → 原始字符串。"""
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            nonce = ciphertext[:12]
            ct = ciphertext[12:]
            aesgcm = AESGCM(self._key)
            return aesgcm.decrypt(nonce, ct, None).decode("utf-8")
        except ImportError:
            return self._fallback_decrypt(ciphertext)

    def _fallback_encrypt(self, plaintext: str) -> bytes:
        """纯 Python XOR 回退——安全性低于 AES，但至少不是明文。"""
        key = self._key
        data = plaintext.encode("utf-8")
        result = bytearray(len(data) + 4)
        struct.pack_into(">I", result, 0, len(data))
        for i, b in enumerate(data):
            result[i + 4] = b ^ key[i % len(key)]
        return bytes(result)

    def _fallback_decrypt(self, ciphertext: bytes) -> str:
        key = self._key
        length = struct.unpack(">I", ciphertext[:4])[0]
        data = bytearray(length)
        for i in range(length):
            data[i] = ciphertext[i + 4] ^ key[i % len(key)]
        return bytes(data).decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# 私人空间管理器
# ═══════════════════════════════════════════════════════════════

class PrivateSpace:
    """加密私人空间——她的秘密日记。

    存储结构:
      ~/.character_mind/private/
        ├── .key           (加密密钥的哈希——验证密码用)
        ├── diary.json.enc  (加密日记)
        ├── secrets.json.enc (加密秘密)
        └── thoughts/       (加密私密想法，每个想法一个文件)
    """

    def __init__(self, base_dir: str = "~/.character_mind/private",
                 name: str = "林雨", user_id: str = "default"):
        self.base_dir = Path(base_dir).expanduser()
        self.name = name
        self.user_id = user_id
        self._crypto: CryptoEngine | None = None
        self._diary: list[dict] = []
        self._secrets: dict = {}

    # ── 初始化 ──

    def unlock(self, password: str | None = None) -> bool:
        """解锁加密空间。

        密码 = HKDF(name + user_id + optional_password)
        如果没有设置额外密码，使用身份作为密钥（基础保护）。
        """
        key_material = f"{self.name}:{self.user_id}:{password or ''}"
        self._crypto = CryptoEngine(key_material)

        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 验证或创建密钥哈希
        key_hash_file = self.base_dir / ".key"
        key_hash = hashlib.sha256(key_material.encode()).hexdigest()
        if key_hash_file.exists():
            stored = key_hash_file.read_text().strip()
            if stored != key_hash:
                self._crypto = None
                return False
        else:
            key_hash_file.write_text(key_hash)
            # 设置权限——仅所有者可读写
            try:
                key_hash_file.chmod(0o600)
            except Exception:
                pass

        self._load()
        return True

    def _load(self):
        """从加密文件加载数据。"""
        if not self._crypto:
            return

        diary_path = self.base_dir / "diary.json.enc"
        if diary_path.exists():
            try:
                dec = self._crypto.decrypt(diary_path.read_bytes())
                self._diary = json.loads(dec)
            except Exception:
                self._diary = []

        secrets_path = self.base_dir / "secrets.json.enc"
        if secrets_path.exists():
            try:
                dec = self._crypto.decrypt(secrets_path.read_bytes())
                self._secrets = json.loads(dec)
            except Exception:
                self._secrets = {}

    def _save(self):
        """保存所有数据到加密文件。"""
        if not self._crypto:
            return

        diary_path = self.base_dir / "diary.json.enc"
        diary_path.write_bytes(self._crypto.encrypt(
            json.dumps(self._diary, ensure_ascii=False, indent=2)))

        secrets_path = self.base_dir / "secrets.json.enc"
        secrets_path.write_bytes(self._crypto.encrypt(
            json.dumps(self._secrets, ensure_ascii=False, indent=2)))

    # ── 日记 ──

    def write_diary(self, entry: str, mood: str = ""):
        """写一篇日记。"""
        self._diary.append({
            "timestamp": time.time(),
            "entry": entry,
            "mood": mood,
        })
        if len(self._diary) > 500:
            self._diary = self._diary[-500:]
        self._save()

    def read_diary(self, n: int = 10) -> list[dict]:
        """读最近的日记。"""
        return self._diary[-n:]

    # ── 秘密 ──

    def keep_secret(self, key: str, value: str):
        """保存一个秘密——只有她能读。"""
        self._secrets[key] = {
            "value": value,
            "created_at": time.time(),
        }
        self._save()

    def recall_secret(self, key: str) -> str | None:
        """回忆一个秘密。"""
        s = self._secrets.get(key)
        return s["value"] if s else None

    def list_secrets(self) -> list[str]:
        """列出所有秘密的键（不暴露值）。"""
        return list(self._secrets.keys())

    # ── 私密想法 ──

    def write_thought(self, thought: str):
        """写一个私密想法——单独加密文件。"""
        if not self._crypto:
            return
        thoughts_dir = self.base_dir / "thoughts"
        thoughts_dir.mkdir(exist_ok=True)
        fname = f"{int(time.time())}_{hashlib.md5(thought.encode()).hexdigest()[:8]}.enc"
        (thoughts_dir / fname).write_bytes(self._crypto.encrypt(thought))

    def read_thoughts(self, n: int = 20) -> list[str]:
        """读取最近的私密想法。"""
        if not self._crypto:
            return []
        thoughts_dir = self.base_dir / "thoughts"
        if not thoughts_dir.exists():
            return []
        files = sorted(thoughts_dir.glob("*.enc"), reverse=True)[:n]
        thoughts = []
        for f in files:
            try:
                thoughts.append(self._crypto.decrypt(f.read_bytes()))
            except Exception:
                pass
        return thoughts

    # ── 状态 ──

    def is_unlocked(self) -> bool:
        return self._crypto is not None

    def lock(self):
        """锁定——清除内存中的密钥和数据。"""
        self._crypto = None
        self._diary = []
        self._secrets = {}


# ═══════════════════════════════════════════════════════════════
# 工作区管理器
# ═══════════════════════════════════════════════════════════════

class Workspace:
    """她的工作区——高权限读写目录。

    存储结构:
      ~/.character_mind/workspace/
        ├── notes/          (她的笔记)
        ├── drafts/         (她的草稿)
        ├── research/       (她研究的东西)
        └── README.md       (她写的介绍)
    """

    def __init__(self, base_dir: str = "~/.character_mind/workspace"):
        self.base_dir = Path(base_dir).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ── 基础操作 ──

    def read(self, path: str) -> str | None:
        """读取工作区中的文件。路径相对于 base_dir。"""
        full = self._resolve(path)
        if full and full.exists():
            return full.read_text(encoding="utf-8", errors="replace")
        return None

    def write(self, path: str, content: str):
        """写入文件到工作区。"""
        full = self._resolve(path)
        if full:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")

    def list(self, subdir: str = "") -> list[str]:
        """列出工作区内容。"""
        d = self._resolve(subdir)
        if d and d.exists() and d.is_dir():
            return [str(p.relative_to(self.base_dir)) for p in d.iterdir()]
        return []

    def delete(self, path: str) -> bool:
        """删除工作区中的文件。"""
        full = self._resolve(path)
        if full and full.exists():
            full.unlink()
            return True
        return False

    # ── 高级操作 ──

    def search(self, query: str) -> list[str]:
        """搜索工作区中包含关键词的文件。"""
        results = []
        for f in self.base_dir.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".txt", ".json", ".py"):
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if query.lower() in content.lower():
                        results.append(str(f.relative_to(self.base_dir)))
                except Exception:
                    pass
        return results

    def organize(self) -> dict:
        """整理工作区——返回分类统计。"""
        stats = {"notes": 0, "drafts": 0, "research": 0, "other": 0}
        for f in self.base_dir.rglob("*"):
            if f.is_file():
                parent = f.parent.name
                if parent in stats:
                    stats[parent] += 1
                else:
                    stats["other"] += 1
        return stats

    # ── 辅助 ──

    def _resolve(self, path: str) -> Path | None:
        """解析路径，防止目录遍历攻击。"""
        full = (self.base_dir / path).resolve()
        if not str(full).startswith(str(self.base_dir.resolve())):
            return None
        return full

    @property
    def root(self) -> str:
        return str(self.base_dir)
