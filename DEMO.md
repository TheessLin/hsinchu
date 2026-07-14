# DEMO 操作流程

本文件記錄第一階段到第二階段的完整展示流程。所有畫面與輸出均為 POC Synthetic Data，不得作為正式政策判斷。

## 0. 啟動系統

Backend:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```powershell
cd D:\forclaude\hsinchu-urban-resilience-poc\frontend
pnpm dev
```

Open:

```text
http://127.0.0.1:5173/
```

## 1. 開啟第一階段圖台

1. 確認新竹市研究範圍與 500m 網格顯示。
2. 切換左側構面，確認地圖即時重新著色。
3. 使用候選區外框開關確認 R-01 外框可顯示或隱藏。
4. 確認頁面顯示模擬資料聲明。

## 2. 選擇 R-01

1. 在下方候選區排名找到 `R-01`。
2. 點擊 R-01 排名列，地圖會縮放至候選區。
3. 點擊 `進入都市更新模擬`。
4. URL 應切換為：

```text
/renewal/R-01
```

## 3. 查看現況

1. 預設 Scenario 為 `Scenario 0｜現況`。
2. 查看 2D 圖台中的街廓、建物、道路與設施。
3. 點選建物，右側會顯示用途、樓層、高度、屋齡、戶數與模擬人口。
4. 查看 KPI 卡片、雷達圖、主要改善、主要負面影響與 AI Decision Summary。

## 4. 切換 Scenario A

1. 左側選擇 `Scenario A｜住宅導向`。
2. 調整住宅戶數、停車席數或開放空間等參數。
3. 點擊 `重新模擬`。
4. 確認 KPI、2D 圖層、Before/After 圖表與 AI 摘要更新。

## 5. 查看 3D 更新結果

1. 中央圖台切換到 `3D`。
2. 使用滑鼠旋轉、縮放查看 LOD1 建物量體。
3. 切換 `更新前`、`更新後`、`透明度比較`。
4. 確認新增、移除與保留建物狀態可辨識。

## 6. 查看 KPI 差異

1. 右側 KPI 卡片檢查方案值、現況值與變化量。
2. 下方 Before/After 長條圖檢查主要 KPI 差異。
3. 確認所有數值均標示單位。

## 7. 切換 Scenario B 及 C

1. 選擇 `Scenario B｜韌性導向`，查看綠地、防災、避難及道路改善 KPI。
2. 選擇 `Scenario C｜交通商業導向`，查看日間人口、商業活動、交通可達 KPI。
3. 每次切換後確認頁面未重新載入，Scenario 狀態直接更新。

## 8. 開啟四方案比較

1. 查看下方 `Scenario 比較表`。
2. 在 `各方案KPI排名` 切換排序目標：
   * 綜合韌性
   * 住宅供給
   * 停車改善
   * 綠地及開放空間
   * 交通可達
   * 防災避難
3. 確認排名列顯示對應 KPI 證據。

## 9. 查看 AI 摘要

1. 右側 `AI Decision Summary` 顯示：
   * 方案一句話摘要
   * 三項主要優勢
   * 三項主要風險
   * 政策權衡
   * 建議補強措施
   * 不確定事項
2. 摘要只引用已計算 KPI，不宣稱正式最佳政策方案。

## 10. 匯出 Scenario 與 KPI

1. 左側 `資料匯出` 區塊選擇目前 Scenario。
2. 依序匯出：
   * Scenario JSON
   * 建物 GeoJSON
   * 道路 GeoJSON
   * 設施 GeoJSON
   * KPI CSV
   * Decision Summary JSON
3. 檔名會包含 `R-01` 與目前 Scenario 代碼。

## 驗收判準

* 第一階段圖台可正常使用。
* R-01 可從候選區排名進入第二階段。
* Scenario 0、A、B、C 可切換且不重新載入頁面。
* Scenario A 可執行重新模擬。
* 3D LOD1 建物量體可顯示。
* KPI 差異、四方案比較、目標排序、AI 摘要與匯出功能可使用。
* 所有頁面均保留 Synthetic Data 聲明。
