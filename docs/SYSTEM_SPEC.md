# 新竹市都市韌性健康度模擬平台

## 第一階段系統開發規格書（POC）

---

## 0. 開發範圍與基本原則

### 0.1 POC定位

本平台以新竹市為空間範圍，建立分析網格，透過具都市空間邏輯的 Synthetic Data，模擬各網格的都市韌性健康度，並提供：

* 韌性健康度地圖
* 六大構面分析
* 網格診斷
* 候選區排名
* 低健康度與高更新潛力區篩選
* 基本權重調整與重新計算

### 0.2 本階段不納入

* 正式政府帳號與權限系統
* 真實人口、地籍、建物或災害個資
* 都市更新建築設計
* 3D Digital Twin
* 真實交通模擬
* CFD風場模擬
* 真實災害工程分析
* 正式政策判定
* 跨機關系統介接
* 即時感測資料串流
* 正式雲端部署與高可用架構

### 0.3 建議POC技術範圍

| 層級   | 技術                     |
| ---- | ---------------------- |
| 前端   | React、TypeScript、Vite  |
| 圖台   | OpenLayers             |
| 圖表   | ECharts                |
| 樣式   | Tailwind CSS           |
| 後端   | FastAPI、Python         |
| 空間處理 | GeoPandas、Shapely      |
| 資料運算 | Pandas、NumPy           |
| 資料格式 | GeoJSON、JSON、CSV       |
| 資料庫  | 第一階段不強制，先採檔案式資料        |
| 執行方式 | 本機開發環境或 Docker Compose |

---

# 1. 系統目標

## 1.1 核心目標

建立一套可以在新竹市分析網格上，模擬並呈現都市韌性健康度的互動式平台。

系統需能回答以下問題：

1. 哪些網格的整體韌性健康度較低？
2. 低健康度主要由哪些構面造成？
3. 哪些區域同時具備低健康度與高更新潛力？
4. 調整六大構面權重後，候選區排名是否改變？
5. 某一候選區周邊是否形成連續性的低健康度群聚？

## 1.2 設計理由

本階段不是建立正式都市治理平台，而是驗證以下概念是否可行：

* Synthetic Data是否能呈現合理都市空間差異。
* 六大構面是否能形成可解釋的健康度分數。
* 圖台是否能協助使用者快速辨識問題區域。
* 候選區篩選是否能支援後續小範圍都市更新模擬。

## 1.3 輸入資料

* 新竹市行政範圍GeoJSON
* 分析網格GeoJSON
* Synthetic Data CSV或GeoJSON
* 六大構面權重設定JSON
* 指標正規化與計分規則JSON

## 1.4 輸出成果

* 全市網格韌性健康度GeoJSON
* 六大構面分數
* 網格診斷結果
* 候選區排名清單
* 候選區群聚GeoJSON
* 前端互動式圖台及圖表

## 1.5 驗收條件

* 可正常載入新竹市網格。
* 每個網格均有六大構面分數及總分。
* 可依總分進行地圖分級設色。
* 可點擊網格查看診斷內容。
* 可產生低健康度與高更新潛力候選區排名。
* 修改權重後可重新計算並更新畫面。

---

# 2. 使用者角色

POC階段僅設計兩種邏輯角色，不實作完整登入驗證。

## 2.1 規劃分析人員

主要使用者，負責：

* 查看全市韌性健康度。
* 切換不同構面。
* 查詢單一網格。
* 調整構面權重。
* 執行候選區篩選。
* 匯出分析結果。

## 2.2 系統開發／資料管理人員

負責：

* 產生Synthetic Data。
* 修改指標參數。
* 重新執行健康度計算。
* 檢查GeoJSON及CSV資料。
* 啟動前後端服務。

## 2.3 POC簡化方式

前端不實作帳號登入，以「分析模式」進入系統。

後端不實作：

* OAuth
* AD／SSO
* RBAC
* 稽核軌跡
* 個人化設定

---

# 3. 功能清單

## 3.1 地圖基礎功能

| 功能編號   | 功能      | 說明            |
| ------ | ------- | ------------- |
| MAP-01 | 新竹市範圍顯示 | 顯示市界及行政區界     |
| MAP-02 | 分析網格顯示  | 顯示固定尺寸或六角形網格  |
| MAP-03 | 分級設色    | 依總分或構面分數顯示顏色  |
| MAP-04 | 圖層切換    | 切換總分、六大構面、候選區 |
| MAP-05 | 網格點擊    | 顯示網格基本資料及診斷   |
| MAP-06 | 地圖縮放    | 放大、縮小、全市定位    |
| MAP-07 | 圖例      | 顯示分數區間與顏色     |
| MAP-08 | 候選區高亮   | 顯示排名前N名候選區    |

## 3.2 韌性分析功能

| 功能編號   | 功能     | 說明            |
| ------ | ------ | ------------- |
| RES-01 | 總健康度計算 | 計算六大構面加權總分    |
| RES-02 | 構面分數計算 | 計算各構面的0～100分  |
| RES-03 | 指標正規化  | 將不同量綱轉為0～100分 |
| RES-04 | 權重調整   | 使用者可調整六大構面權重  |
| RES-05 | 重新計算   | 套用新權重並更新結果    |
| RES-06 | 分數分級   | 依固定級距或分位數分級   |

## 3.3 網格診斷功能

| 功能編號   | 功能   | 說明            |
| ------ | ---- | ------------- |
| DIA-01 | 基本資訊 | 網格編號、行政區、都市類型 |
| DIA-02 | 雷達圖  | 顯示六大構面分數      |
| DIA-03 | 弱項辨識 | 列出最低的三個構面     |
| DIA-04 | 指標明細 | 顯示構面內各項指標     |
| DIA-05 | 診斷文字 | 依規則產生簡短診斷     |
| DIA-06 | 鄰近比較 | 與相鄰網格或全市平均比較  |

## 3.4 候選區篩選功能

| 功能編號   | 功能    | 說明            |
| ------ | ----- | ------------- |
| CAN-01 | 門檻篩選  | 依健康度及更新潛力門檻篩選 |
| CAN-02 | 候選分數  | 計算候選區優先分數     |
| CAN-03 | 候選排名  | 依候選分數排序       |
| CAN-04 | 空間群聚  | 合併相鄰候選網格      |
| CAN-05 | 最小面積  | 排除面積過小的零碎區    |
| CAN-06 | 前N名顯示 | 顯示前5、10或20名   |
| CAN-07 | 結果匯出  | 匯出CSV及GeoJSON |

## 3.5 Synthetic Data功能

| 功能編號   | 功能      | 說明            |
| ------ | ------- | ------------- |
| SYN-01 | 都市類型分配  | 指定各網格都市類型     |
| SYN-02 | 條件式資料生成 | 依都市類型產生合理數值   |
| SYN-03 | 空間趨勢    | 依中心、邊緣或走廊產生差異 |
| SYN-04 | 隨機種子    | 固定seed以重現資料   |
| SYN-05 | 資料驗證    | 檢查欄位、值域及缺漏    |
| SYN-06 | 資料匯出    | 產出CSV及GeoJSON |

---

# 4. 使用者操作流程

## 4.1 主要操作流程

```text
進入平台
  ↓
載入新竹市範圍及網格
  ↓
顯示全市韌性健康度總覽
  ↓
選擇分析圖層
  ├─ 整體健康度
  ├─ 六大構面
  └─ 更新潛力
  ↓
點擊特定網格
  ↓
查看網格診斷、雷達圖及指標明細
  ↓
設定候選區篩選條件
  ↓
執行候選區排名
  ↓
在地圖顯示候選網格或候選群聚區
  ↓
查看前N名候選區
  ↓
匯出CSV或GeoJSON
```

## 4.2 權重調整流程

```text
開啟權重設定
  ↓
調整六大構面權重
  ↓
系統檢查權重總和是否為100%
  ↓
送出重新計算
  ↓
後端重算總健康度與排名
  ↓
前端更新地圖、圖表及候選區結果
```

## 4.3 Synthetic Data產生流程

```text
讀取新竹市網格
  ↓
依空間位置分配都市類型
  ↓
依都市類型套用參數範圍
  ↓
加入空間趨勢與受控隨機變異
  ↓
檢查值域與欄位完整性
  ↓
輸出CSV及GeoJSON
```

---

# 5. 前端頁面架構

POC建議採單頁Dashboard，不設計過多頁面。

## 5.1 路由架構

```text
/
└── Dashboard
    ├── Map View
    ├── Layer Control
    ├── Summary Panel
    ├── Grid Diagnosis Drawer
    ├── Candidate Ranking Panel
    └── Weight Setting Modal
```

## 5.2 Dashboard版面

### A. 頂部工具列

內容：

* 系統名稱
* 資料版本
* 重新載入
* 權重設定
* 匯出結果

### B. 左側控制面板

內容：

* 圖層選擇
* 分數分級方式
* 候選區篩選條件
* 前N名數量
* 執行篩選按鈕

### C. 中央地圖

內容：

* 新竹市市界
* 行政區界
* 分析網格
* 候選區圖層
* 圖例
* 縮放控制
* 全圖定位

### D. 右側摘要面板

內容：

* 全市平均健康度
* 最低健康度行政區
* 低健康度網格數量
* 候選區數量
* 六大構面平均分數長條圖
* 健康度分布直方圖

### E. 網格診斷抽屜

點擊網格後展開：

* 網格編號
* 行政區
* 都市類型
* 總健康度
* 六構面雷達圖
* 最弱三項構面
* 指標明細表
* 鄰近網格比較
* 規則式診斷文字

### F. 候選區排名面板

內容：

* 排名
* 候選區編號
* 涵蓋網格數
* 面積
* 平均健康度
* 更新潛力
* 候選優先分數
* 查看地圖位置

## 5.3 前端主要元件

```text
src/
├── components/
│   ├── map/
│   │   ├── ResilienceMap.tsx
│   │   ├── MapLegend.tsx
│   │   ├── LayerSwitcher.tsx
│   │   └── MapToolbar.tsx
│   ├── dashboard/
│   │   ├── SummaryCards.tsx
│   │   ├── DimensionBarChart.tsx
│   │   └── ScoreHistogram.tsx
│   ├── diagnosis/
│   │   ├── GridDiagnosisDrawer.tsx
│   │   ├── ResilienceRadarChart.tsx
│   │   └── IndicatorTable.tsx
│   ├── candidates/
│   │   ├── CandidateFilter.tsx
│   │   └── CandidateRankingTable.tsx
│   └── settings/
│       └── WeightSettingModal.tsx
```

## 5.4 前端驗收條件

* 解析度1280×720以上可正常操作。
* 地圖、控制面板及摘要區不互相遮擋。
* 圖層切換後，地圖顏色正確更新。
* 點擊網格可顯示診斷內容。
* 權重錯誤時顯示提示。
* 候選區表格與地圖可互相定位。

---

# 6. 後端API清單

API前綴：

```text
/api/v1
```

## 6.1 系統與設定API

### GET `/health`

用途：確認服務是否正常。

輸出：

```json
{
  "status": "ok",
  "service": "hsinchu-resilience-api",
  "version": "0.1.0"
}
```

### GET `/config`

用途：取得目前構面權重及系統參數。

### PUT `/config/weights`

用途：更新構面權重。

輸入：

```json
{
  "built_environment": 0.25,
  "hazard_evacuation": 0.20,
  "transport_accessibility": 0.15,
  "social_demographic": 0.15,
  "living_health": 0.15,
  "renewal_potential": 0.10
}
```

驗證：

* 每項權重介於0與1。
* 權重總和等於1。
* 允許浮點誤差小於0.0001。

---

## 6.2 空間資料API

### GET `/boundaries/city`

用途：取得新竹市市界GeoJSON。

### GET `/boundaries/districts`

用途：取得行政區界GeoJSON。

### GET `/grids`

用途：取得分析網格。

查詢參數：

* `dimension`
* `score_min`
* `score_max`
* `district`
* `urban_type`
* `candidate_only`

### GET `/grids/{grid_id}`

用途：取得單一網格完整資料。

### GET `/grids/{grid_id}/neighbors`

用途：取得相鄰網格資料。

---

## 6.3 韌性計算API

### POST `/resilience/calculate`

用途：依目前或指定權重重新計算。

輸入：

```json
{
  "weights": {
    "built_environment": 0.25,
    "hazard_evacuation": 0.20,
    "transport_accessibility": 0.15,
    "social_demographic": 0.15,
    "living_health": 0.15,
    "renewal_potential": 0.10
  },
  "normalization": "min_max"
}
```

輸出：

```json
{
  "calculation_id": "calc_20260713_001",
  "grid_count": 1234,
  "city_average": 63.42,
  "updated_at": "2026-07-13T16:00:00+08:00"
}
```

### GET `/resilience/summary`

用途：取得全市統計摘要。

### GET `/resilience/distribution`

用途：取得健康度分數分布。

---

## 6.4 網格診斷API

### GET `/diagnosis/{grid_id}`

輸出內容：

* 網格基本資料
* 六大構面分數
* 指標分數
* 最弱構面
* 與全市平均差異
* 鄰近網格平均
* 診斷文字

---

## 6.5 候選區API

### POST `/candidates/filter`

輸入：

```json
{
  "health_score_max": 50,
  "renewal_potential_min": 65,
  "min_cluster_grids": 3,
  "min_cluster_area_m2": 30000,
  "top_n": 10,
  "include_single_grid": false
}
```

### GET `/candidates`

用途：取得最近一次候選區結果。

### GET `/candidates/{candidate_id}`

用途：取得單一候選區詳細資料。

### GET `/candidates/export.csv`

用途：匯出候選區CSV。

### GET `/candidates/export.geojson`

用途：匯出候選區GeoJSON。

---

## 6.6 Synthetic Data API

POC可先以命令列腳本為主，API為選配。

### POST `/synthetic/generate`

輸入：

```json
{
  "seed": 42,
  "grid_source": "hsinchu_grid.geojson",
  "scenario": "baseline"
}
```

### GET `/synthetic/status`

用途：查看Synthetic Data版本與產生資訊。

---

# 7. Synthetic Data Schema

## 7.1 網格基本欄位

| 欄位                    | 型別     | 說明              |
| --------------------- | ------ | --------------- |
| grid_id               | string | 網格唯一識別碼         |
| district              | string | 行政區             |
| urban_type            | string | 都市空間類型          |
| centroid_x            | number | 中心點X座標          |
| centroid_y            | number | 中心點Y座標          |
| area_m2               | number | 網格面積            |
| distance_to_center_km | number | 距模擬市中心距離        |
| density_level         | string | low／medium／high |

## 7.2 都市類型

```text
old_residential       老舊住宅區
commercial_core       商業核心區
emerging_residential  新興住宅區
industrial_area       產業／工業區
urban_edge            都市邊緣區
mixed_use             混合使用區
open_space             開放空間周邊
```

## 7.3 建成環境欄位

| 欄位                       |     單位 |    合理值域 |
| ------------------------ | -----: | ------: |
| avg_building_age         |      年 |    0～60 |
| old_building_ratio       |    0～1 |     0～1 |
| avg_road_width           |     公尺 |    3～30 |
| building_coverage_ratio  |    0～1 | 0.1～0.9 |
| floor_area_ratio         | number |   0.2～8 |
| open_space_ratio         |    0～1 |   0～0.8 |
| building_condition_index |  0～100 |   0～100 |

## 7.4 災害與避難欄位

| 欄位                        |    單位 |   合理值域 |
| ------------------------- | ----: | -----: |
| flood_risk_index          | 0～100 |  0～100 |
| fire_risk_index           | 0～100 |  0～100 |
| evacuation_site_distance  |    公尺 | 0～3000 |
| evacuation_capacity_ratio |   0～2 |    0～2 |
| fire_accessibility        | 0～100 |  0～100 |
| emergency_route_access    | 0～100 |  0～100 |

## 7.5 交通與可達性欄位

| 欄位                        |    單位 |   合理值域 |
| ------------------------- | ----: | -----: |
| transit_stop_distance     |    公尺 | 0～3000 |
| transit_service_index     | 0～100 |  0～100 |
| road_connectivity_index   | 0～100 |  0～100 |
| pedestrian_accessibility  | 0～100 |  0～100 |
| parking_pressure_index    | 0～100 |  0～100 |
| avg_commute_accessibility | 0～100 |  0～100 |

## 7.6 社會人口欄位

全部為合成統計值，不代表真實人口。

| 欄位                         |     單位 |      合理值域 |
| -------------------------- | -----: | --------: |
| synthetic_population       |      人 |    0～5000 |
| population_density         | 人／平方公里 |   0～50000 |
| elderly_ratio              |    0～1 | 0.03～0.35 |
| child_ratio                |    0～1 | 0.03～0.30 |
| vulnerable_household_ratio |    0～1 | 0.01～0.35 |
| daytime_population_ratio   | number |     0.3～4 |
| community_support_index    |  0～100 |     0～100 |

## 7.7 生活機能與健康欄位

| 欄位                          |    單位 |  合理值域 |
| --------------------------- | ----: | ----: |
| medical_accessibility       | 0～100 | 0～100 |
| daily_service_accessibility | 0～100 | 0～100 |
| green_space_accessibility   | 0～100 | 0～100 |
| school_accessibility        | 0～100 | 0～100 |
| food_accessibility          | 0～100 | 0～100 |
| heat_stress_index           | 0～100 | 0～100 |
| environmental_quality       | 0～100 | 0～100 |

## 7.8 更新潛力欄位

| 欄位                        |    單位 |  合理值域 |
| ------------------------- | ----: | ----: |
| redevelopment_need        | 0～100 | 0～100 |
| land_assembly_feasibility | 0～100 | 0～100 |
| public_land_ratio         |   0～1 |   0～1 |
| underused_land_ratio      |   0～1 |   0～1 |
| development_intensity_gap | 0～100 | 0～100 |
| strategic_location_index  | 0～100 | 0～100 |
| renewal_potential_score   | 0～100 | 0～100 |

## 7.9 空間邏輯生成規則

### 老舊住宅區

* 建物平均屋齡較高。
* 老舊建物比例較高。
* 道路較窄。
* 消防可及性較低。
* 更新需求較高。
* 土地整合可行性不一定高。

### 商業核心區

* 日間人口較高。
* 公共運輸服務較佳。
* 停車壓力較高。
* 開放空間比例偏低。
* 醫療及生活機能較佳。

### 新興住宅區

* 建物較新。
* 道路較寬。
* 綠地較多。
* 建物狀況較佳。
* 更新需求較低。

### 都市邊緣區

* 公共運輸服務較低。
* 醫療與生活機能可及性較低。
* 建築密度較低。
* 土地整合可行性可能較高。

### 高密度區

* 人口密度較高。
* 停車壓力較高。
* 開放空間壓力較高。
* 避難容量壓力較高。

## 7.10 Synthetic Data生成公式

每個指標不採完全無條件亂數，而採：

```text
指標值 =
都市類型基準值
+ 空間趨勢修正
+ 密度修正
+ 關聯指標修正
+ 受控隨機誤差
```

例如：

```text
avg_building_age =
urban_type_base_age
+ distance_effect
+ density_effect
+ random_normal(0, 4)
```

受控隨機誤差建議限制在基準值的5%～15%。

固定：

```python
np.random.seed(42)
```

確保相同版本可重現。

---

# 8. 都市韌性指標及計算公式

## 8.1 六大構面權重

| 構面        | 代碼 |  權重 |
| --------- | -- | --: |
| 建成環境韌性    | BE | 25% |
| 災害與避難韌性   | HE | 20% |
| 交通與可達性韌性  | TA | 15% |
| 社會人口韌性    | SD | 15% |
| 生活機能與健康韌性 | LH | 15% |
| 更新潛力      | RP | 10% |

## 8.2 指標方向

### 正向指標

數值越高代表韌性越好，例如：

* 道路寬度
* 開放空間比例
* 消防可及性
* 公共運輸服務
* 醫療可及性
* 社區支持指數

### 負向指標

數值越高代表韌性越差，例如：

* 建物屋齡
* 淹水風險
* 火災風險
* 停車壓力
* 熱壓力
* 弱勢家戶比例

## 8.3 Min-Max正規化

### 正向指標

```text
Score(x) = 100 × (x - xmin) / (xmax - xmin)
```

### 負向指標

```text
Score(x) = 100 × (xmax - x) / (xmax - xmin)
```

### 邊界處理

```text
Score = min(100, max(0, Score))
```

如 `xmax = xmin`，該指標統一給50分並記錄警告。

## 8.4 建成環境韌性

```text
BE =
0.20 × 建物屋齡分數
+ 0.15 × 老舊建物比例分數
+ 0.20 × 道路寬度分數
+ 0.15 × 開放空間比例分數
+ 0.15 × 建物狀況分數
+ 0.15 × 建築密度適宜度分數
```

建築密度適宜度不直接認定越高越好，可採目標區間計分。

例如目標建蔽率為0.35～0.60：

```text
位於目標區間：80～100分
低於或高於目標區間：依偏離程度遞減
```

## 8.5 災害與避難韌性

```text
HE =
0.20 × 淹水風險反向分數
+ 0.15 × 火災風險反向分數
+ 0.15 × 避難場所距離反向分數
+ 0.15 × 避難容量分數
+ 0.20 × 消防可及性分數
+ 0.15 × 緊急道路可及性分數
```

## 8.6 交通與可達性韌性

```text
TA =
0.20 × 大眾運輸站點距離反向分數
+ 0.20 × 大眾運輸服務分數
+ 0.20 × 道路連通性分數
+ 0.15 × 步行可及性分數
+ 0.10 × 停車壓力反向分數
+ 0.15 × 通勤可達性分數
```

## 8.7 社會人口韌性

```text
SD =
0.20 × 高齡比例反向分數
+ 0.15 × 幼兒比例反向分數
+ 0.20 × 弱勢家戶比例反向分數
+ 0.15 × 日夜人口平衡分數
+ 0.15 × 社區支持分數
+ 0.15 × 人口密度適宜度分數
```

注意：

高齡、幼兒及弱勢比例在POC中代表「服務與支援需求」，不代表族群本身具有負面價值。

## 8.8 生活機能與健康韌性

```text
LH =
0.20 × 醫療可及性分數
+ 0.15 × 日常服務可及性分數
+ 0.15 × 綠地可及性分數
+ 0.10 × 學校可及性分數
+ 0.10 × 食物可及性分數
+ 0.15 × 熱壓力反向分數
+ 0.15 × 環境品質分數
```

## 8.9 更新潛力

更新潛力是「後續改善與更新可行性」，不是一般韌性的同義詞。

```text
RP =
0.25 × 更新需求
+ 0.20 × 土地整合可行性
+ 0.10 × 公有土地比例分數
+ 0.15 × 低度利用土地比例分數
+ 0.15 × 開發強度落差分數
+ 0.15 × 策略區位分數
```

## 8.10 總健康度

```text
Total Health Score =
0.25 × BE
+ 0.20 × HE
+ 0.15 × TA
+ 0.15 × SD
+ 0.15 × LH
+ 0.10 × RP
```

分數範圍：

```text
0～100
```

## 8.11 健康度分級

|       分數 | 等級 | 說明      |
| -------: | -- | ------- |
|   80～100 | A  | 韌性健康度良好 |
| 65～79.99 | B  | 韌性健康度尚可 |
| 50～64.99 | C  | 局部構面需改善 |
| 35～49.99 | D  | 韌性健康度偏低 |
|  0～34.99 | E  | 優先關注    |

POC預設採固定級距，避免不同資料版本造成分位數級距不一致。

---

# 9. GeoJSON資料結構

## 9.1 網格FeatureCollection

```json
{
  "type": "FeatureCollection",
  "name": "hsinchu_resilience_grid",
  "crs": {
    "type": "name",
    "properties": {
      "name": "EPSG:4326"
    }
  },
  "metadata": {
    "data_type": "synthetic",
    "version": "0.1.0",
    "generated_at": "2026-07-13T16:00:00+08:00",
    "seed": 42
  },
  "features": []
}
```

## 9.2 單一網格Feature

```json
{
  "type": "Feature",
  "id": "GRID_000001",
  "geometry": {
    "type": "Polygon",
    "coordinates": []
  },
  "properties": {
    "grid_id": "GRID_000001",
    "district": "東區",
    "urban_type": "old_residential",
    "area_m2": 10000,
    "synthetic_population": 860,
    "scores": {
      "built_environment": 42.6,
      "hazard_evacuation": 48.2,
      "transport_accessibility": 67.5,
      "social_demographic": 51.4,
      "living_health": 63.1,
      "renewal_potential": 78.3,
      "total_health": 55.6
    },
    "health_grade": "C",
    "is_candidate": true,
    "candidate_priority_score": 71.2,
    "weakest_dimensions": [
      "built_environment",
      "hazard_evacuation",
      "social_demographic"
    ]
  }
}
```

## 9.3 候選區Feature

```json
{
  "type": "Feature",
  "id": "CAND_001",
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": []
  },
  "properties": {
    "candidate_id": "CAND_001",
    "rank": 1,
    "grid_count": 8,
    "area_m2": 80000,
    "districts": ["東區"],
    "avg_health_score": 41.8,
    "avg_renewal_potential": 79.5,
    "priority_score": 82.4,
    "dominant_urban_type": "old_residential",
    "major_weaknesses": [
      "built_environment",
      "hazard_evacuation"
    ]
  }
}
```

## 9.4 座標系統

* 後端空間分析建議使用TWD97／TM2適當分區或其他公尺制投影。
* 前端API輸出統一轉為EPSG:4326。
* 面積與距離不得直接在EPSG:4326下計算。

---

# 10. 候選區篩選邏輯

## 10.1 第一層：網格資格篩選

預設條件：

```text
總健康度 ≤ 50
且
更新潛力 ≥ 65
```

可增加條件：

```text
建成環境韌性 ≤ 55
或
災害與避難韌性 ≤ 55
```

網格資格公式：

```text
Eligible =
Total Health Score ≤ Health Threshold
AND Renewal Potential ≥ Renewal Threshold
```

## 10.2 第二層：候選優先分數

將低健康度轉為缺口分數：

```text
Health Deficit = 100 - Total Health Score
```

候選優先分數：

```text
Priority Score =
0.45 × Health Deficit
+ 0.35 × Renewal Potential
+ 0.10 × Spatial Continuity
+ 0.10 × Strategic Location
```

其中：

* `Spatial Continuity`：相鄰合格網格越多，分數越高。
* `Strategic Location`：使用Synthetic Data中的策略區位分數。

## 10.3 第三層：空間相鄰判定

兩個網格符合以下任一條件，即視為相鄰：

* Polygon邊界接觸。
* 共用邊界長度大於指定門檻。
* 網格中心點距離小於網格邊長的1.5倍。

建議優先採用：

```python
geometry.touches(other_geometry)
```

如使用方格網，需排除僅角點接觸的情況，可改用共用邊界長度判斷。

## 10.4 第四層：候選區群聚

流程：

1. 找出所有合格網格。
2. 建立相鄰網格圖。
3. 以Connected Components找出連續群聚。
4. 將同群聚網格合併為候選區。
5. 計算群聚統計值。
6. 排除不符合最小網格數或最小面積者。
7. 依優先分數排序。

## 10.5 預設篩選參數

| 參數       |        預設值 |
| -------- | ---------: |
| 健康度上限    |         50 |
| 更新潛力下限   |         65 |
| 最小群聚網格數  |          3 |
| 最小群聚面積   | 30,000平方公尺 |
| 顯示候選區數量  |         10 |
| 是否保留單一網格 |          否 |

## 10.6 候選區群聚分數

```text
Cluster Priority Score =
0.50 × 群聚內網格平均優先分數
+ 0.20 × 群聚內最低健康度缺口
+ 0.15 × 群聚連續性分數
+ 0.15 × 群聚面積適宜度
```

## 10.7 輸出格式

候選區結果至少包含：

* candidate_id
* rank
* grid_ids
* grid_count
* area_m2
* avg_health_score
* min_health_score
* avg_renewal_potential
* priority_score
* dominant_urban_type
* major_weaknesses
* geometry

## 10.8 驗收條件

* 不符合門檻的網格不得進入候選清單。
* 相鄰網格可正確合併。
* 不相鄰網格不得錯誤合併。
* 排名依候選分數由高至低排列。
* 相同輸入及參數產生相同結果。

---

# 11. 專案資料夾結構

```text
hsinchu-resilience-poc/
├── README.md
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── system-spec.md
│   ├── api-spec.md
│   ├── data-dictionary.md
│   └── calculation-rules.md
├── data/
│   ├── raw/
│   │   ├── hsinchu_boundary.geojson
│   │   └── district_boundary.geojson
│   ├── generated/
│   │   ├── analysis_grid.geojson
│   │   ├── synthetic_indicators.csv
│   │   ├── resilience_grid.geojson
│   │   └── candidate_areas.geojson
│   └── config/
│       ├── weights.json
│       ├── indicator_rules.json
│       └── synthetic_profiles.json
├── backend/
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── grids.py
│   │   │   ├── resilience.py
│   │   │   ├── diagnosis.py
│   │   │   ├── candidates.py
│   │   │   └── synthetic.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── constants.py
│   │   ├── models/
│   │   │   ├── grid.py
│   │   │   ├── weights.py
│   │   │   └── candidate.py
│   │   ├── schemas/
│   │   │   ├── grid.py
│   │   │   ├── resilience.py
│   │   │   └── candidate.py
│   │   ├── services/
│   │   │   ├── grid_service.py
│   │   │   ├── synthetic_service.py
│   │   │   ├── scoring_service.py
│   │   │   ├── diagnosis_service.py
│   │   │   └── candidate_service.py
│   │   └── utils/
│   │       ├── geo.py
│   │       ├── normalization.py
│   │       └── validators.py
│   ├── scripts/
│   │   ├── generate_grid.py
│   │   ├── generate_synthetic_data.py
│   │   ├── calculate_scores.py
│   │   └── build_candidates.py
│   └── tests/
│       ├── test_normalization.py
│       ├── test_scoring.py
│       ├── test_candidates.py
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/
│       │   └── DashboardPage.tsx
│       ├── components/
│       ├── services/
│       │   └── api.ts
│       ├── stores/
│       │   └── resilienceStore.ts
│       ├── types/
│       │   ├── grid.ts
│       │   ├── resilience.ts
│       │   └── candidate.ts
│       └── utils/
│           ├── mapStyle.ts
│           └── scoreFormat.ts
└── scripts/
    ├── setup.sh
    └── run-dev.sh
```

---

# 12. 開發階段拆解

## 階段一：專案骨架與基礎資料

### 目標

建立前後端專案、環境設定及新竹市範圍資料。

### 輸入

* 新竹市範圍GeoJSON
* 行政區界GeoJSON
* 技術框架設定

### 工作項目

1. 建立Git專案。
2. 建立React＋TypeScript＋Vite。
3. 建立FastAPI專案。
4. 建立資料夾結構。
5. 建立`/health` API。
6. 建立基礎地圖頁。
7. 顯示新竹市範圍。

### 輸出

* 可啟動的前端
* 可啟動的後端
* 新竹市範圍地圖

---

## 階段二：分析網格建立

### 目標

建立覆蓋新竹市的固定分析網格。

### 工作項目

1. 將市界轉為公尺制座標。
2. 建立100公尺×100公尺方格。
3. 裁切至新竹市範圍。
4. 產生grid_id。
5. 計算中心點與面積。
6. 轉換為EPSG:4326輸出。

### 合理預設

POC預設採100公尺方格。

若效能不佳，可改為200公尺方格。

### 輸出

```text
analysis_grid.geojson
```

---

## 階段三：Synthetic Data產生

### 目標

依都市類型及空間規則產生指標資料。

### 工作項目

1. 定義都市類型。
2. 建立各類型基準參數。
3. 依位置、密度及距離分配類型。
4. 產生各項合成指標。
5. 加入指標間關聯。
6. 驗證值域。
7. 輸出CSV及GeoJSON。

### 輸出

```text
synthetic_indicators.csv
synthetic_grid.geojson
```

---

## 階段四：韌性計算引擎

### 目標

完成指標正規化、構面計算及總分計算。

### 工作項目

1. 建立指標方向設定。
2. 完成Min-Max正規化。
3. 完成六構面計算。
4. 完成總分計算。
5. 完成健康度分級。
6. 撰寫單元測試。

### 輸出

```text
resilience_grid.geojson
```

---

## 階段五：後端API

### 目標

提供前端所需資料服務。

### 工作項目

1. 網格查詢API。
2. 摘要統計API。
3. 單一網格診斷API。
4. 權重設定API。
5. 重新計算API。
6. 錯誤處理及資料驗證。

---

## 階段六：圖台與儀表板

### 目標

完成主要互動介面。

### 工作項目

1. OpenLayers圖台。
2. 網格分級設色。
3. 圖層切換。
4. 地圖圖例。
5. 全市摘要卡。
6. 構面平均圖表。
7. 健康度分布圖。
8. 網格點擊互動。

---

## 階段七：網格診斷

### 目標

完成單一網格詳細分析。

### 工作項目

1. 六構面雷達圖。
2. 指標明細表。
3. 弱項排序。
4. 全市平均比較。
5. 鄰近網格比較。
6. 規則式診斷文字。

診斷文字範例：

```text
本網格整體健康度偏低，主要弱項為建成環境與災害避難。
建物屋齡偏高且道路寬度不足，可能降低消防與緊急通行能力。
此內容為合成資料模擬結果，不代表真實現況。
```

---

## 階段八：候選區篩選與排名

### 目標

完成低健康度及高更新潛力區域篩選。

### 工作項目

1. 門檻篩選。
2. 候選分數計算。
3. 相鄰網格判定。
4. 候選區群聚。
5. 排名表。
6. 地圖高亮。
7. CSV及GeoJSON匯出。

---

## 階段九：整合測試與文件

### 目標

完成POC可操作版本。

### 工作項目

1. 前後端整合測試。
2. 資料重現性測試。
3. API測試。
4. 基本效能測試。
5. README。
6. 啟動操作說明。
7. 已知限制說明。

---

# 13. 每階段驗收條件

| 階段 | 驗收條件                                |
| -- | ----------------------------------- |
| 一  | 前後端可啟動，`/health`回傳正常，地圖顯示新竹市範圍      |
| 二  | 網格完整覆蓋市界，每個網格具有唯一ID、面積及中心點          |
| 三  | 所有網格均有完整Synthetic Data，無超出值域及必要欄位缺漏 |
| 四  | 六構面與總分均介於0～100，相同資料可重現相同結果          |
| 五  | 核心API可正常回傳JSON或GeoJSON，錯誤輸入可回傳合理訊息  |
| 六  | 可切換總分及六構面圖層，顏色、圖例及摘要同步更新            |
| 七  | 點擊網格可顯示雷達圖、弱項、指標明細及診斷文字             |
| 八  | 可依門檻產生候選區、完成群聚、排名及檔案匯出              |
| 九  | README可讓另一位開發者完成安裝、啟動與測試            |

## 13.1 整體POC完成標準

* 一個指令或兩個指令可啟動前後端。
* 首頁可於合理時間內載入。
* 可從全市總覽操作到單一網格診斷。
* 可完成候選區篩選及結果匯出。
* 所有畫面標示「Synthetic Data／概念驗證」。
* 系統不宣稱分析結果代表真實新竹市現況。

---

# 14. 測試案例

## 14.1 正規化測試

### TC-NORM-001 正向指標最小值

輸入：

```text
x = xmin
```

預期：

```text
score = 0
```

### TC-NORM-002 正向指標最大值

輸入：

```text
x = xmax
```

預期：

```text
score = 100
```

### TC-NORM-003 負向指標最大值

輸入：

```text
x = xmax
```

預期：

```text
score = 0
```

### TC-NORM-004 相同最大最小值

輸入：

```text
xmin = xmax
```

預期：

* 回傳50分。
* 產生警告紀錄。
* 系統不中斷。

---

## 14.2 權重測試

### TC-WEIGHT-001 正常權重

輸入總和：

```text
1.0
```

預期：

* 設定成功。
* 重新計算成功。

### TC-WEIGHT-002 權重總和錯誤

輸入總和：

```text
0.95
```

預期：

* HTTP 422或400。
* 回傳「權重總和必須為1」。

### TC-WEIGHT-003 負權重

輸入：

```text
built_environment = -0.1
```

預期：

* 拒絕設定。
* 不覆蓋原設定。

---

## 14.3 韌性分數測試

### TC-SCORE-001 分數值域

預期：

* 所有構面分數介於0～100。
* 總健康度介於0～100。

### TC-SCORE-002 加權計算

使用固定測試資料手動計算結果。

預期：

* 程式計算結果與人工結果誤差小於0.01。

### TC-SCORE-003 資料重現性

條件：

```text
seed = 42
```

預期：

* 兩次產生的Synthetic Data完全相同。

---

## 14.4 網格API測試

### TC-API-001 查詢存在網格

預期：

* HTTP 200。
* 回傳指定grid_id。

### TC-API-002 查詢不存在網格

預期：

* HTTP 404。
* 回傳可讀錯誤訊息。

### TC-API-003 條件篩選

輸入：

```text
score_max = 50
```

預期：

* 回傳網格的總健康度均小於或等於50。

---

## 14.5 候選區測試

### TC-CAN-001 符合雙門檻

網格：

```text
health_score = 45
renewal_potential = 75
```

預期：

```text
eligible = true
```

### TC-CAN-002 健康度不符合

網格：

```text
health_score = 60
renewal_potential = 80
```

預期：

```text
eligible = false
```

### TC-CAN-003 更新潛力不符合

網格：

```text
health_score = 40
renewal_potential = 50
```

預期：

```text
eligible = false
```

### TC-CAN-004 相鄰群聚

條件：

* 4個合格網格彼此相鄰。
* 最小群聚網格數為3。

預期：

* 形成1個候選區。
* grid_count等於4。

### TC-CAN-005 零碎網格排除

條件：

* 單一合格網格。
* `include_single_grid = false`。

預期：

* 不產生候選區。

### TC-CAN-006 排名穩定性

條件：

* 相同資料及相同篩選參數。

預期：

* 多次執行排名一致。

---

## 14.6 前端互動測試

### TC-UI-001 圖層切換

操作：

* 從總健康度切換至災害與避難韌性。

預期：

* 網格顏色更新。
* 圖例標題及區間更新。
* 其他面板不異常。

### TC-UI-002 網格點擊

預期：

* 開啟診斷抽屜。
* 顯示正確grid_id。
* 雷達圖與API資料一致。

### TC-UI-003 排名定位

操作：

* 點擊候選區排名第1名。

預期：

* 地圖縮放至候選區。
* 候選區高亮。
* 顯示候選區摘要。

### TC-UI-004 API失敗

條件：

* 後端暫時無法連線。

預期：

* 顯示錯誤提示。
* 畫面不得完全白屏。

---

## 14.7 效能測試

POC合理目標：

| 項目     |  目標 |
| ------ | --: |
| 初始頁面載入 | 5秒內 |
| 網格圖層切換 | 2秒內 |
| 單一網格診斷 | 1秒內 |
| 權重重新計算 | 5秒內 |
| 候選區篩選  | 5秒內 |

測試環境需記錄：

* 網格數量
* CPU
* 記憶體
* 瀏覽器版本

---

# 15. 已知限制

## 15.1 資料限制

1. 所有指標資料均為Synthetic Data。
2. Synthetic Data不代表新竹市真實人口、建物、交通或災害情況。
3. 都市類型與空間趨勢為模型假設。
4. 不得將輸出結果作為正式都市更新範圍認定。
5. 不得將網格結果解讀為特定居民或社區的真實狀況。

## 15.2 模型限制

1. 指標權重為POC預設值，尚未經專家德爾菲法或AHP驗證。
2. Min-Max正規化易受極端值影響。
3. 總分會簡化不同構面間的複雜關係。
4. 高分可能掩蓋單一構面極低的情況。
5. 更新潛力包含模擬可行性，不等於實際都市更新可行性。
6. 候選區排名僅是規則式排序，不是政策建議。

## 15.3 空間分析限制

1. 網格大小會影響分析結果。
2. 邊界網格的面積可能小於標準網格。
3. 網格分析可能產生可變空間單元問題。
4. 相鄰判定僅考慮幾何關係，未考慮河川、鐵路或高架道路阻隔。
5. 群聚區不代表真實街廓或都市更新單元。

## 15.4 系統限制

1. 第一階段以檔案式資料為主，不使用正式空間資料庫。
2. 不支援多人同時編輯。
3. 不支援正式帳號、權限及稽核。
4. 不保證大規模網格的前端渲染效能。
5. 不處理正式備援、容錯、災難復原。
6. 不實作跨系統API介接。
7. 匯出資料僅供POC展示。

## 15.5 操作與展示限制

所有主要畫面及匯出成果應固定顯示：

```text
本系統為概念驗證版本，使用合成資料進行模擬。
分析結果不代表新竹市真實現況，亦不得作為正式政策或都市更新判定依據。
```

---

# 16. 建議Codex分階段執行順序

為避免一次產生過多程式碼，建議依下列順序交付Codex：

```text
Task 1：建立專案骨架及README
Task 2：建立新竹市分析網格腳本
Task 3：建立Synthetic Data Schema及資料產生器
Task 4：建立正規化與韌性計算引擎
Task 5：建立FastAPI基礎API
Task 6：建立React Dashboard及OpenLayers地圖
Task 7：建立網格診斷功能
Task 8：建立候選區篩選與群聚
Task 9：建立權重調整與重新計算
Task 10：建立匯出、測試及Docker啟動方式
```

每一個Task均應要求Codex：

1. 只修改該階段相關檔案。
2. 不預先實作後續大型功能。
3. 提供完整檔案路徑。
4. 提供啟動或測試指令。
5. 提供本階段驗收方式。
6. 保留Synthetic Data與POC警語。
7. 測試通過後再進入下一階段。
