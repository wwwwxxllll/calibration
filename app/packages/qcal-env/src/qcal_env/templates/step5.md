# Step 5: QubitT1

## 实验目的

本步骤用于拟合量子比特的能量弛豫时间 T1。

## 实验背景

量子比特被 pi pulse 激发到 e 态后，会随时间逐渐弛豫回 g 态。通过改变激发后到读取前的等待时间，并测量读取响应随等待时间的变化，可以得到能量弛豫曲线。

本实验对等待时间进行扫描，并使用指数模型提取 T1 时间常数。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `QubitT1`。

## 实验输入

量子比特驱动频率设置为 `{QubitFreq} Hz`，pi pulse 幅度设置为 `{amp180} a.u.`。

驱动脉冲采用高斯波形，高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

等待时间列表由 `numstep = {numstep}` 和 `timeStep = {timeStep}` 生成。

读取频率设置为 `{ReadoutFreq} Hz`，读取脉冲幅度设置为 `{readout_amp} a.u.`。

每个等待时间点重复采样 `{roundRobin}` 次，并对每个等待时间点下的 I、Q 和幅值 A 取平均。

## 拟合

每个等待时间点对应一组经过平均后的测量结果，包括平均 I 值、平均 Q 值和平均幅值 A。

本步骤使用 `{fit_model}` 模型对弛豫曲线进行拟合。拟合得到的时间常数为 `{T1} s`，拟合决定系数 R² 为 `{r_squared}`。

## 实验结果

根据 T1 等待时间扫描结果和 `{fit_model}` 拟合结果，拟合得到的能量弛豫时间为：

`T1 = {T1} s`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
