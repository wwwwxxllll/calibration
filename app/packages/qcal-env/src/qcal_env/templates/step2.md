# Step 2: SweepQubit

## 实验目的

本步骤用于拟合量子比特的驱动频率。

## 实验背景

在确定读取腔频率后，需要进一步确定量子比特的驱动频率。通过在固定读取频率下扫描量子比特驱动频率，并测量读取响应，可以得到量子比特谱线。

本实验对量子比特驱动频率进行扫描，并使用拟合模型提取谱线中心频率。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `SweepQubit`。

## 实验输入

量子比特驱动频率从 `{QubitStartFreq1} Hz` 扫描到 `{QubitStopFreq1} Hz`，频率步长为 `{Qubitstep1} Hz`。

量子比特驱动脉冲采用高斯波形，驱动幅度参数为 `{amp180} a.u.`，高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

读取频率设置为 `{ReadoutFreq} Hz`，读取脉冲幅度设置为 `{readout_amp} a.u.`。

每个频点重复采样 `{roundRobin}` 次，并对每个频点下的 I、Q 和幅值 A 取平均。

## 拟合

每个量子比特驱动频点对应一组经过平均后的测量结果，包括平均 I 值、平均 Q 值和平均幅值 A。

本步骤使用 `{fit_model}` 模型对量子比特谱线进行拟合。拟合得到的中心频率为 `{center_hz} Hz`，半高宽为 `{half_width_hz} Hz`，拟合决定系数 R² 为 `{r_squared}`。

## 实验结果

根据量子比特频率扫描结果和 `{fit_model}` 拟合结果，拟合得到的量子比特驱动频率为：

`QubitFreq = {QubitFreq} Hz`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

Agent 确认该结果合理后，可使用上述 `candidate_id` 调用 `confirm_calibration`；确认前不会写入生效标定值。

拟合图地址如下：

{plot_path}
