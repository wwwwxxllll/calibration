# Step 6.2: Echo

## 实验目的

本步骤用于拟合 Echo 保护下的量子比特退相干时间 T2 Echo。

## 实验背景

Echo 实验通过 pi/2 - pi - pi/2 脉冲序列抵消部分低频噪声造成的相位漂移。相比 Ramsey 实验，Echo 序列通常可以得到更长的退相干时间。

本实验对 Echo 延迟时间进行扫描，并使用 Echo 衰减模型提取 T2 Echo。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `Echo`。

## 实验输入

量子比特驱动频率设置为 `{QubitFreq} Hz`，pi pulse 幅度参数设置为 `{amp180} a.u.`。

pi/2 - pi - pi/2 pulse 使用高斯波形，高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

Echo 延迟列表由 `numstep = {numstep}` 和 `timeStep = {timeStep}` 生成。

读取频率设置为 `{ReadoutFreq} Hz`，读取脉冲幅度设置为 `{readout_amp} a.u.`。

每个延迟时间点重复采样 `{roundRobin}` 次，并对每个延迟时间点下的 I、Q 和幅值 A 取平均。

## 拟合

每个 Echo 延迟点对应一组经过平均后的测量结果，包括平均 I 值、平均 Q 值和平均幅值 A。

本步骤使用 `{fit_model}` 模型对 Echo 衰减曲线进行拟合。拟合得到的 Echo 退相干时间为 `{T2_echo} s`，拟合决定系数 R² 为 `{r_squared}`。

## 实验结果

根据 Echo 延迟扫描结果和 `{fit_model}` 拟合结果，拟合得到的 Echo 退相干时间为：

`T2Echo = {T2_echo} s`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
