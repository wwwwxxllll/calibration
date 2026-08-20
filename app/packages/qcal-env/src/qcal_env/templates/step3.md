# Step 3: PowerRabi

## 实验目的

本步骤用于拟合量子比特 pi pulse 的驱动幅度。

## 实验背景

在确定量子比特驱动频率后，需要标定能够将量子比特从 g 态翻转到 e 态的 pi pulse 幅度。通过固定驱动频率并扫描驱动幅度，可以观察到 Rabi 振荡。

本实验对量子比特驱动幅度进行扫描，并使用拟合模型提取 pi pulse 对应的幅度。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `PowerRabi`。

## 实验输入

量子比特驱动频率固定为 `{QubitFreq} Hz`。

驱动脉冲采用高斯波形，幅度扫描由 `numstep = {numstep}` 和 `RabiStep = {RabiStep}` 生成。高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

读取频率设置为 `{ReadoutFreq} Hz`，读取脉冲幅度设置为 `{readout_amp} a.u.`。

每个幅度点重复采样 `{roundRobin}` 次，并对每个幅度点下的 I、Q 和幅值 A 取平均。

## 拟合

每个驱动幅度点对应一组经过平均后的测量结果，包括平均 I 值、平均 Q 值和平均幅值 A。

本步骤使用 `{fit_model}` 模型对 Rabi 振荡曲线进行拟合。拟合得到的 pi pulse 幅度为 `{amp180_fit} a.u.`，振荡周期为 `{period} a.u.`，拟合决定系数 R² 为 `{r_squared}`。

## 实验结果

根据 Power Rabi 扫描结果和 `{fit_model}` 拟合结果，拟合得到的 pi pulse 幅度为：

`amp180 = {amp180_fit} a.u.`

本次结果已保存为待 Agent 审核的标定候选值。除 `amp180` 外，本步骤使用的 `mysigma` 和 `coeff` 也会作为同一轮校准的候选标定值等待确认。

- `candidate_ids`: `{candidate_ids}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
