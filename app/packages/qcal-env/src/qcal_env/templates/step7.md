# Step 7: SingleShotHistogram

## 实验目的

本步骤用于分析 g 态和 e 态的 single-shot 读取分布，并标定判态质量。

## 实验背景

single-shot 读取需要根据一次测量得到的 IQ 点判断量子比特处于 g 态还是 e 态。为了评估判态质量，需要分别采集 g 态和 e 态的读取分布。

本实验分别采集 g 态和 e 态的 single-shot 数据，并通过两个态的分布中心、判态阈值和判态保真度评估读出分离度。

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

根据两个分布的交界位置，得到判态阈值 `{single_shot_threshold}`，判态保真度为 `{fidelity}`，Rayleigh 分离比为 `{RayleighRatio}`。

## 实验结果

根据 g/e 态 single-shot 数据和 `{fit_model}` 分析结果，得到的 Rayleigh 分离比为：

`RayleighRatio = {RayleighRatio}`

判态阈值为：

`single_shot_threshold = {single_shot_threshold} a.u.`

判态保真度为：

`fidelity = {fidelity}`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
