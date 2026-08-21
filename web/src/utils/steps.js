// 校准流程步骤 → 参数键 的映射，用于把候选/已确认标定值关联到对应的步骤。
export const STEP_PARAM_KEY = {
  Step1: 'readout.frequency.g',
  Step2: 'qubit.frequency',
  Step3: 'qubit.pi_pulse.amplitude',
  Step4: 'readout.frequency.e',
  Step5: 'qubit.t1',
  'Step6.1': 'qubit.t2',
  'Step6.2': 'qubit.t2_echo',
  Step7: 'readout.single_shot.rayleigh_ratio'
};
