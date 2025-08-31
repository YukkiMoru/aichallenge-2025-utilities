
# セットアップ手順

## 1. pythonの仮想環境（venv）の作成
ターミナルで以下のコマンドを実行してください。

```sh
python -m venv .venv
```

## 2. 仮想環境の有効化

### Windowsの場合
```sh
.venv\Scripts\activate
```

### Linux/macOSの場合
```sh
source .venv/bin/activate
```

## 3. 必要なパッケージのインストール
仮想環境内で以下のコマンドを実行してください。

```sh
pip install -r requirements.txt
```

### パッケージインストールが壊れた・うまくいかない場合
キャッシュを使わずに再インストールすることで解決する場合があります：
```sh
pip install --no-cache-dir -r requirements.txt
```

追加で `matplotlib` も必要な場合：
```sh
pip install matplotlib
```

---

## 補足：VSCodeでの仮想環境設定とPython導入方法

### Pythonのインストール方法
1. 公式サイト（https://www.python.org/downloads/）からPython最新版をダウンロードし、インストールしてください。
2. インストール時に「Add Python to PATH」に必ずチェックを入れてください。
3. インストール後、ターミナルで `python --version` を実行し、バージョンが表示されればOKです。

### VSCodeで仮想環境のPythonインタープリターを選択する方法
1. まず、VSCode拡張機能「Python」（Microsoft製）をインストールしてください。
	- 拡張機能ビューで「Python」と検索し、インストールします。
2. VSCode左下の「Python」または「インタープリター」部分をクリックします。
3. 一覧から `.venv` など仮想環境のPythonを選択します。
	- もし表示されない場合は「インタープリターの選択」から手動でパスを指定できます。
4. 正しく選択されると、ターミナルやデバッグ実行時に仮想環境が使われます。

---