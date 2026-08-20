# Step 4: SweepReadoutE

## 实验目的

本步骤用于拟合量子比特处于 e 态时的读取腔频率，并计算读取腔与量子比特之间的频率偏移。

## 实验背景

量子比特处于不同能级状态时，读取腔的等效共振频率会发生偏移。Step 1 得到的是量子比特处于 g 态时的读取腔频率。本步骤在读取前施加 pi pulse，将量子比特制备到 e 态，然后再次扫描读取腔频率。

本实验通过比较 e 态读取腔频率和 g 态读取腔频率，得到两种读出态之间的频率差。

## 实验信息

校准流程编号为 `{calibration_id}`，本次 Action 编号为 `{action_id}`，实验开始时间为 `{timestamp}`。实验名称为 `SweepReadoutE`。

## 实验输入

读取频率从 `{ReadoutStartFreq1} Hz` 扫描到 `{ReadoutStopFreq1} Hz`，频率步长为 `{Readoutstep1} Hz`。

读取脉冲幅度设置为 `{readout_amp} a.u.`。

在每次读取前，使用量子比特频率 `{QubitFreq} Hz` 和 pi pulse 幅度 `{amp180} a.u.` 将量子比特制备到 e 态。高斯宽度参数为 `{mysigma}`，缩放系数为 `{coeff}`。

每个读取频点重复采样 `{roundRobin}` 次，并对每个频点下的 I、Q 和幅值 A 取平均。

## 拟合

每个读取频点对应一组经过平均后的测量结果，包括平均 I 值、平均 Q 值和平均幅值 A。

本步骤使用 `{fit_model}` 模型对 e 态读取腔响应进行拟合。拟合得到的 e 态读取腔中心频率为 `{center_e_hz} Hz`，半高宽为 `{half_width_hz} Hz`，拟合决定系数 R² 为 `{r_squared}`。

g 态读取腔中心频率为 `{center_g_hz} Hz`。两者相减得到 `chi = {chi_hz} Hz`。

## 实验结果

根据 e 态读取腔频率扫描结果和 `{fit_model}` 拟合结果，拟合得到的 e 态读取频率为：

`ReadoutFreqE = {center_e_hz} Hz`

计算得到的读取腔频率偏移为：

`chi = {chi_hz} Hz`

本次结果已保存为待 Agent 审核的标定候选值：

- `candidate_id`: `{candidate_id}`
- `status`: `{candidate_status}`

拟合图地址如下：

{plot_path}
