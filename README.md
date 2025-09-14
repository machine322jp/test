# Puyo Puyo Simulator / ぷよぷよシミュレータ

This project provides a Puyo Puyo simulator implemented in Python with
`pygame`.
Python と `pygame` で実装されたぷよぷよシミュレータです。

## Features / 機能
- 6x14 board with four colors (red, green, blue, yellow)
  - 6x14 の盤面と 4 色（赤・緑・青・黄）のぷよ
- Real-time play in a `pygame` window with keyboard controls
  - `pygame` ウィンドウでのリアルタイムプレイ（← → 移動、Z/X 回転、下ハードドロップ、上アンドゥ、R リセット）
- Groups of four or more connected puyos disappear and gravity is applied
  - 4 個以上つながったぷよを消去し重力を適用
- Next and double-next preview plus beam-search-based best arrangement view
  - ネクスト・ダブルネクスト表示とビームサーチによる最適連鎖プレビュー
- Undo stack for reverting hard drops
  - ハードドロップのアンドゥ機能

## Running / 実行方法
```bash
python puyo.py
```

## Testing / テスト
```bash
pytest
```
