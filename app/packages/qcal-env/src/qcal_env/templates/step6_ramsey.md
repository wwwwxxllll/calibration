# Step 6.1: Ramsey

## 实验目的

本步骤用于拟合量子比特的 Ramsey 退相干时间 T2*。

## 实验背景

Ramsey 实验通过两个 pi/2 pulse 构造相干叠加态，并在两个脉冲之间插入不同延迟时间。随着延迟时间增加，量子比特相干性逐渐衰减，同时可能出现由失谐引起的 Ramsey 振荡。

本实验对 Ramsey 延迟时间进行扫描，并使用 Ramsey 衰减模型提取 T2*。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `Ramsey`。

## 实验输入

量子比特驱动频率设置为 `{QubitFreq} Hz`，pi pulse 幅度参数设置为 `{amp180} a.u.`。

两个 pi/2 pulse 使用高斯波形，高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

Ramsey 延迟列表由 `numstep = {numstep}` 和 `timeStep = {timeStep}` 生成。第二个 pi/2 pulse 的相位序列由 `numstep` 在后端内部生成。

读取频率设置为 `{ReadoutFreq} Hz`，读取脉冲幅度设置为 `{readout_amp} a.u.`。

每个延迟时间点重复采样 `{roundRobin}` 次，并对每个延迟时间点下的 I、Q 和幅值 A 取平均。

## 拟合

每个 Ramsey 延迟点对应一组经过平均后的测量结果，包括平均 I 值、平均 Q 值和平均幅值 A。

本步骤使用 `{fit_model}` 模型对 Ramsey 振荡衰减曲线进行拟合。拟合得到的退相干时间为 `{T2_star} s`，失谐频率为 `{detuning_hz} Hz`，拟合决定系数 R² 为 `{r_squared}`。

## 实验结果

根据 Ramsey 延迟扫描结果和 `{fit_model}` 拟合结果，拟合得到的 Ramsey 退相干时间为：

`T2Star = {T2_star} s`

拟合得到的失谐频率为：

`detuning = {detuning_hz} Hz`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
