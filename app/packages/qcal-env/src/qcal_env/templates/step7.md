# Step 7: SingleShotHistogram

## 实验目的

本步骤用于分析 g 态和 e 态的 single-shot 读取分布，并标定判态阈值。

## 实验背景

single-shot 读取需要根据一次测量得到的 IQ 点判断量子比特处于 g 态还是 e 态。为了评估判态质量，需要分别采集 g 态和 e 态的读取分布。

本实验分别采集 g 态和 e 态的 single-shot 数据，通过二维高斯拟合得到两个态的分布中心与协方差，沿判别轴投影后计算判态阈值，并用三条判据检查读出分离质量。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `SingleShotHistogram`。

## 实验输入

读取频率设置为 `{ReadoutFreq} Hz`，读取脉冲幅度设置为 `{readout_amp} a.u.`。

g 态数据直接读取获得。

e 态数据在读取前先使用量子比特频率 `{QubitFreq} Hz` 和 pi pulse 幅度 `{amp180} a.u.` 将量子比特制备到 e 态。高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

g 态和 e 态分别采样 `{roundRobin}` 次。

直方图分箱数设置为 `{bin}`。

## 拟合

本步骤使用 `{fit_model}` 模型对 g 态和 e 态的 single-shot 分布进行汇总分析。拟合得到 g 态分布中心 `{g_center}`，e 态分布中心 `{e_center}`。

沿两分布中心连线（判别轴）投影，g 态投影中心为 0，e 态投影中心为分离度 `{separation:.4g}`。g/e 投影的高斯半高全宽分别为 `{fwhm_g:.4g}` / `{fwhm_e:.4g}`。

根据投影分布的交界位置，得到判态阈值 `{single_shot_threshold} a.u.`，判态概率 gg = `{g_correct:.4f}`，ee = `{e_correct:.4f}`。

## 判据检查

本步骤用三条判据检查单发读出分离质量，作为 Agent 是否确认该候选值的门槛：

1. **二维高斯拟合优度**：R²_g = `{r2_g:.3f}`，R²_e = `{r2_e:.3f}`（需均 > 0.9）→ `{r2_pass}`

2. **瑞利判据**：分离度 d = `{separation:.4g}` vs FWHM_g + FWHM_e = `{fwhm_sum:.4g}`（需 d > FWHM_g + FWHM_e）→ `{rayleigh_pass}`

3. **判态概率**：gg = `{g_correct:.4f}`，ee = `{e_correct:.4f}`（需均 > 0.9）→ `{gg_ee_pass}`

综合判定：**`{verdict}`**

## 实验结果

根据 g/e 态 single-shot 数据和 `{fit_model}` 分析结果，得到的判态阈值为：

`single_shot_threshold = {single_shot_threshold} a.u.`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
