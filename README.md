# Nablarch Handler Queue Designer (NHQD)

[Nablarch](https://nablarch.github.io/) フレームワーク向けハンドラキュー自動設計ツール。

## 概要

NHQDは構造化されたYAML要件定義から、最適なNablarchハンドラキュー構成を自動生成します。ルールベース推論エンジンとDAGベースのトポロジカルソートにより、全てのハンドラ順序制約を確実に充足します。

### 対応アプリケーション種別

| 種別 | 説明 |
|------|------|
| `web` | Webアプリケーション（HTML/JSP） |
| `rest` | RESTful Webサービス（JAX-RS） |
| `batch` | 都度起動バッチ |
| `batch_resident` | 常駐バッチ |
| `mom_messaging` | MOMメッセージング |
| `http_messaging` | HTTPメッセージング |

## アーキテクチャ

```
┌──────────────────────────────────────────────────────────┐
│              Nablarch Handler Queue Designer              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  パーサー    │──→│  推論エンジン  │──→│  出力生成器   │  │
│  │  (YAML)    │   │ (DAGソート)  │   │  (XML/MD)    │  │
│  └────────────┘   └──────┬───────┘   └──────────────┘  │
│                          │                               │
│                ┌─────────┴─────────┐                     │
│                │  ナレッジベース      │                     │
│                │ ・ハンドラカタログ    │                     │
│                │ ・順序制約          │                     │
│                │ ・設計パターン      │                     │
│                └───────────────────┘                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## インストール

```bash
pip install -e ".[dev]"
```

## 使い方

### 要件定義からハンドラキューを生成

```bash
nhqd generate examples/web_app_requirements.yaml -o output/
```

### 既存構成の検証

```bash
nhqd validate path/to/handler-queue-config.xml
```

### 利用可能なハンドラ一覧

```bash
nhqd list-handlers
```

## 要件定義ファイルフォーマット

```yaml
project:
  name: "顧客管理システム"
  type: web  # web | rest | batch | batch_resident | mom_messaging | http_messaging

requirements:
  database:
    enabled: true
    type: PostgreSQL
    transaction: required
  authentication:
    enabled: true
    type: session
    login_check: true
  security:
    csrf_protection: true
    secure_headers: true
```

完全な例は `examples/web_app_requirements.yaml` を参照。

## 順序制約

NHQDは以下のハンドラ順序制約を強制します：

| ID | ルール | 重要度 |
|----|--------|--------|
| C-01 | トランザクションはDB接続より後 | 致命的 |
| C-02 | ディスパッチハンドラは末尾 | 致命的 |
| C-03 | RoutesMapping内ハンドラはRoutesMapping内部に配置 | 致命的 |
| C-04 | HTTPメッセージングパーサーはレスポンスハンドラより後 | 致命的 |
| C-05 | HTTPメッセージングパーサーはスレッドコンテキストより後 | 致命的 |
| C-06 | ヘルスチェックはレスポンスハンドラより後 | 警告 |
| C-07 | LoopHandlerはMultiThreadExecutionHandlerより後 | 致命的 |
| C-08 | DataReadHandlerはLoopHandlerより後 | 致命的 |
| C-09 | GlobalErrorHandlerは先頭付近 | 警告 |
| C-10 | インターセプタの実行順序は明示必要 | 警告 |

## 開発

```bash
# 開発用依存関係のインストール
pip install -e ".[dev]"

# テスト実行
pytest

# リント
ruff check src/ tests/
```

## ライセンス

Apache License 2.0 - 詳細は [LICENSE](LICENSE) を参照。
