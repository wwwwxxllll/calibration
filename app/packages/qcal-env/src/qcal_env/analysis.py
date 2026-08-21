"""Step1-Step7 fitting and plotting owned by Env."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
import numpy as np
from scipy.optimize import curve_fit

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from qcal_contracts import RawResult

PLOT_AXES_BY_EXPERIMENT: dict[str, tuple[str, str]] = {
    "SweepReadout": ("f (GHz)", "A"),
    "SweepQubit": ("f (GHz)", "A"),
    "PowerRabi": ("amp", "I"),
    "PowerRabiQ": ("amp", "Q"),
    "PowerRabiIQ": ("I", "Q"),
    "SweepReadoutE": ("f (GHz)", "A"),
    "QubitT1": ("T (us)", "I"),
    "Ramsey": ("T (us)", "I"),
    "Echo": ("T (us)", "I"),
    "SingleShotHistogram": ("I", "Q"),
}


def lorentzian(
    frequency_hz: np.ndarray,
    offset: float,
    height: float,
    center_hz: float,
    half_width_hz: float,
) -> np.ndarray:
    width2 = half_width_hz**2
    return offset + height * width2 / ((frequency_hz - center_hz) ** 2 + width2)


def lorentzian_with_linear_baseline(
    frequency_hz: np.ndarray,
    offset: float,
    slope_per_hz: float,
    height: float,
    center_hz: float,
    half_width_hz: float,
) -> np.ndarray:
    width2 = half_width_hz**2
    return offset + slope_per_hz * (frequency_hz - center_hz) + height * width2 / ((frequency_hz - center_hz) ** 2 + width2)


def half_cos_model(x: np.ndarray, amplitude: float, omega: float, offset: float) -> np.ndarray:
    """功率 Rabi 半余弦模型，等价 MATLAB 的 RabihalfCosfitfun：I = A*cos(omega*x) + C。

    无相位项；omega = pi/amp180，故 amp180 = pi/omega。
    """
    return amplitude * np.cos(omega * x) + offset


def exponential_decay(x: np.ndarray, baseline: float, amplitude: float, decay_s: float) -> np.ndarray:
    return baseline + amplitude * np.exp(-x / decay_s)


def exponential_rise(x: np.ndarray, plateau: float, amplitude: float, decay_s: float) -> np.ndarray:
    return plateau - amplitude * np.exp(-x / decay_s)


def ramsey_model(
    x: np.ndarray,
    baseline: float,
    amplitude: float,
    frequency_hz: float,
    phase: float,
    decay_s: float,
) -> np.ndarray:
    return baseline + amplitude * np.cos(2.0 * np.pi * frequency_hz * x + phase) * np.exp(-x / decay_s)


def ramsey_single_frequency_model(
    x: np.ndarray,
    baseline: float,
    amplitude: float,
    frequency_hz: float,
    phase: float,
    decay_rate: float,
) -> np.ndarray:
    return baseline + amplitude * np.sin(2.0 * np.pi * frequency_hz * x + phase) * np.exp(-x * decay_rate)


def ramsey_double_frequency_model(
    x: np.ndarray,
    baseline: float,
    amplitude_1: float,
    frequency_1_hz: float,
    phase_1: float,
    decay_rate_1: float,
    amplitude_2: float,
    frequency_2_hz: float,
    phase_2: float,
    decay_rate_2: float,
) -> np.ndarray:
    return baseline + (
        amplitude_1 * np.sin(2.0 * np.pi * frequency_1_hz * x + phase_1) * np.exp(-x * decay_rate_1)
        + amplitude_2 * np.sin(2.0 * np.pi * frequency_2_hz * x + phase_2) * np.exp(-x * decay_rate_2)
    )


def ramsey_damped_model(
    x: np.ndarray,
    baseline: float,
    decay_amplitude: float,
    oscillation_amplitude: float,
    frequency_hz: float,
    phase: float,
    decay_time_s: float,
) -> np.ndarray:
    """Ramsey/Echo 信号 = 常数基线 + 与振荡同 T2 的衰减直流项 + 阻尼振荡。

    信号 0.5·(1+cos)·exp(-t/T2) 展开后含一个不振荡的衰减项 0.5·exp(-t/T2)，
    单频阻尼正弦（常数基线）表示不了它，会把它错算进衰减率，导致 T2 拟合错误。
    """
    envelope = np.exp(-x / decay_time_s)
    return baseline + decay_amplitude * envelope + oscillation_amplitude * envelope * np.sin(2.0 * np.pi * frequency_hz * x + phase)


def fit_lorentzian(frequencies_hz: np.ndarray, response: np.ndarray) -> dict[str, object]:
    frequencies_hz = np.asarray(frequencies_hz, dtype=float)
    response = np.asarray(response, dtype=float)
    finite = np.isfinite(frequencies_hz) & np.isfinite(response)
    frequencies_hz = frequencies_hz[finite]
    response = response[finite]
    if frequencies_hz.size < 5 or np.any(np.diff(frequencies_hz) <= 0.0):
        raise ValueError("Lorentzian 拟合至少需要 5 个严格递增的有效频点。")

    step_hz = float(np.median(np.diff(frequencies_hz)))
    span_hz = float(np.ptp(frequencies_hz))
    response_span = max(float(np.ptp(response)), np.finfo(float).eps)
    linear_slope, linear_intercept = np.polyfit(frequencies_hz - frequencies_hz[0], response, deg=1)
    trend = linear_intercept + linear_slope * (frequencies_hz - frequencies_hz[0])
    residual_from_trend = response - trend
    center_candidates = {
        int(np.argmin(response)),
        int(np.argmax(response)),
        int(np.argmax(np.abs(residual_from_trend))),
        int(response.size // 2),
    }
    width_candidates = [
        max(2.0 * step_hz, span_hz / 40.0),
        max(4.0 * step_hz, span_hz / 20.0),
        max(8.0 * step_hz, span_hz / 10.0),
    ]
    lower = (
        float(np.min(response) - 2.0 * response_span),
        -10.0 * response_span / span_hz,
        -5.0 * response_span,
        frequencies_hz[0],
        0.1 * step_hz,
    )
    upper = (
        float(np.max(response) + 2.0 * response_span),
        10.0 * response_span / span_hz,
        5.0 * response_span,
        frequencies_hz[-1],
        span_hz,
    )
    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for index in center_candidates:
        center_guess = float(frequencies_hz[index])
        offset_guess = float(linear_intercept + linear_slope * (center_guess - frequencies_hz[0]))
        height_guess = float(response[index] - offset_guess)
        if abs(height_guess) < np.finfo(float).eps:
            height_guess = float(response[index] - np.median(response))
        for width_guess in width_candidates:
            try:
                params, _ = curve_fit(
                    lorentzian_with_linear_baseline,
                    frequencies_hz,
                    response,
                    p0=(offset_guess, float(linear_slope), height_guess, center_guess, width_guess),
                    bounds=(lower, upper),
                    maxfev=30_000,
                )
            except (RuntimeError, ValueError):
                continue
            fitted_candidate = lorentzian_with_linear_baseline(frequencies_hz, *params)
            residual_sum = float(np.sum((response - fitted_candidate) ** 2))
            if best is None or residual_sum < best[0]:
                best = (residual_sum, params, fitted_candidate)
    if best is None:
        raise ValueError("Lorentzian 拟合失败，请检查频点范围和有效数据。")
    _, params, fitted_at_data = best
    residual = response - fitted_at_data
    total = float(np.sum((response - np.mean(response)) ** 2))
    r_squared = 1.0 - float(np.sum(residual**2)) / total if total else 0.0
    fit_frequencies_hz = np.linspace(
        float(frequencies_hz[0]),
        float(frequencies_hz[-1]),
        max(800, int(frequencies_hz.size * 8)),
    )
    fit_response = lorentzian_with_linear_baseline(fit_frequencies_hz, *params)
    return {
        "model": "Lorentzian + linear baseline",
        "center_hz": float(params[3]),
        "half_width_hz": float(params[4]),
        "r_squared": r_squared,
        "parameters": [float(value) for value in params],
        "fit_frequencies_hz": fit_frequencies_hz,
        "fit_response": fit_response,
    }


def estimate_iq_rotation_angle(i_values: np.ndarray, q_values: np.ndarray) -> float:
    """估计 IQ 平面旋转角，对齐 MATLAB 的 polyfit(I,Q,1) + atan(a1(1))。

    MATLAB 原意：对 I-Q 散点做线性拟合 Q = a·I + b，取斜率角度 atan(a)。
    """
    finite = np.isfinite(i_values) & np.isfinite(q_values)
    i = np.asarray(i_values, dtype=float)[finite]
    q = np.asarray(q_values, dtype=float)[finite]
    if i.size < 2:
        return 0.0
    slope, _ = np.polyfit(i, q, 1)
    return float(np.arctan(slope))


def rotate_iq(
    i_values: np.ndarray,
    q_values: np.ndarray,
    angle_rad: float,
) -> tuple[np.ndarray, np.ndarray]:
    """旋转 IQ 平面，对齐 MATLAB 的 R(θ)=[cosθ, sinθ; -sinθ, cosθ]。

    返回 (旋转后的 I, 旋转后的 Q)。
    """
    i = np.asarray(i_values, dtype=float)
    q = np.asarray(q_values, dtype=float)
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    i_rot = c * i + s * q
    q_rot = -s * i + c * q
    return i_rot, q_rot


def fit_power_rabi(amplitudes: np.ndarray, response: np.ndarray) -> dict[str, object]:
    x, y = _finite_xy(amplitudes, response, minimum=8, label="Power Rabi")
    span = max(float(np.ptp(y)), np.finfo(float).eps)
    step = float(np.median(np.diff(x)))
    centered = y - np.mean(y)
    crossings = np.where(np.diff(np.signbit(centered)))[0]
    guess_period = float(2.0 * step * max(len(x) / 4.0, 1.0))
    if crossings.size >= 2:
        guess_period = float(2.0 * np.median(np.diff(x[crossings[: min(crossings.size, 6)]])))
    omega_guess = 2.0 * np.pi / max(guess_period, step)
    # MATLAB 初值约定：x0 = [-0.5*(max-min), pi/amp180, 0.5*(max+min)]，振幅取负。
    params, _ = curve_fit(
        half_cos_model,
        x,
        y,
        p0=(-0.5 * span, omega_guess, float(np.mean(y))),
        bounds=(
            (-2.0 * span, 2.0 * np.pi / (4.0 * float(np.ptp(x))), float(np.min(y) - span)),
            (2.0 * span, 2.0 * np.pi / step, float(np.max(y) + span)),
        ),
        maxfev=20_000,
    )
    fitted = half_cos_model(x, *params)
    amplitude_fit, omega_fit, offset_fit = params
    pi_amplitude = float(np.pi / omega_fit)
    return {
        "model": "Half-cosine Rabi",
        "pi_amplitude": pi_amplitude,
        "period": float(2.0 * np.pi / omega_fit),
        "omega": float(omega_fit),
        "i_g": float(offset_fit - amplitude_fit),
        "i_e": float(offset_fit + amplitude_fit),
        "r_squared": _r_squared(y, fitted),
        "parameters": [float(value) for value in params],
        "fit_x": x,
        "fit_response": fitted,
    }


def fit_t1(waiting_time_s: np.ndarray, response: np.ndarray) -> dict[str, object]:
    x, y = _finite_xy(waiting_time_s, response, minimum=5, label="T1")
    if y[-1] < y[0]:
        y = y[0] + y[-1] - y
    span = max(float(np.ptp(y)), np.finfo(float).eps)
    params, _ = curve_fit(
        exponential_rise,
        x,
        y,
        p0=(float(y[-1]), float(y[-1] - y[0]), max(float(np.ptp(x)) / 2.0, np.finfo(float).eps)),
        bounds=(
            (float(np.min(y) - span), 0.0, max(float(np.median(np.diff(x))) * 0.1, np.finfo(float).eps)),
            (float(np.max(y) + span), 2.0 * span, max(float(np.ptp(x)) * 10.0, np.finfo(float).eps)),
        ),
        maxfev=20_000,
    )
    fitted = exponential_rise(x, *params)
    return {
        "model": "Exponential rise",
        "decay_time_s": float(params[2]),
        "r_squared": _r_squared(y, fitted),
        "parameters": [float(value) for value in params],
        "fit_x": x,
        "fit_response": fitted,
    }


def fit_ramsey(waiting_time_s: np.ndarray, response: np.ndarray, *, ramsey_angle_hz: float) -> dict[str, object]:
    x, y = _finite_xy(waiting_time_s, response, minimum=8, label="Ramsey")
    span = max(float(np.ptp(y)), np.finfo(float).eps)
    min_decay_rate = 1.0 / max(float(np.ptp(x)) * 10.0, np.finfo(float).eps)
    max_decay_rate = 1.0 / max(float(np.median(np.diff(x))) * 0.1, np.finfo(float).eps)
    frequency_bound_hz = max(10.0e6, 5.0 * abs(float(ramsey_angle_hz)))
    decay_guess = 1.0 / max(float(np.ptp(x)) / 2.0, np.finfo(float).eps)

    # 主模型：常数基线 + 与振荡同 T2 的衰减直流项 + 阻尼振荡（物理正确的 Ramsey/Echo 形式）。
    # 单频阻尼正弦把那个不振荡的衰减项错算进衰减率，会错报 T2，所以优先用这个模型。
    min_decay_time_s = max(float(np.median(np.diff(x))) * 0.1, np.finfo(float).eps)
    max_decay_time_s = max(float(np.ptp(x)) * 10.0, np.finfo(float).eps)
    decay_time_guess = float(np.ptp(x)) / 2.0
    damped_candidates: list[tuple[float, np.ndarray]] = []
    for frequency_guess in _frequency_guesses(x, y, ramsey_angle_hz=ramsey_angle_hz):
        for phase_guess in (0.0, 0.5 * np.pi, -0.5 * np.pi, np.pi):
            for decay_amp_guess in (0.0, 0.25 * span, -0.25 * span):
                try:
                    params, _ = curve_fit(
                        ramsey_damped_model,
                        x,
                        y,
                        p0=(float(np.mean(y)), decay_amp_guess, 0.5 * span, frequency_guess, phase_guess, decay_time_guess),
                        bounds=(
                            (float(np.min(y) - span), -2.0 * span, -2.0 * span, -frequency_bound_hz, -2.0 * np.pi, min_decay_time_s),
                            (float(np.max(y) + span), 2.0 * span, 2.0 * span, frequency_bound_hz, 2.0 * np.pi, max_decay_time_s),
                        ),
                        maxfev=30_000,
                    )
                except (RuntimeError, ValueError):
                    continue
                damped_candidates.append((float(np.sum((y - ramsey_damped_model(x, *params)) ** 2)), params))
    if damped_candidates:
        _, params = min(damped_candidates, key=lambda item: item[0])
        params = _positive_frequency_params(params, frequency_indices=(3,), phase_indices=(4,))
        fitted = ramsey_damped_model(x, *params)
        detuning_hz = float(params[3] - ramsey_angle_hz)
        t2_s = float(params[5])
        plot_x = np.linspace(float(x[0]), float(x[-1]), max(800, int(x.size * 20)))
        plot_response = ramsey_damped_model(plot_x, *params)
        return {
            "model": "Damped oscillation with decaying offset",
            "t2_s": t2_s,
            "detuning_hz": detuning_hz,
            "ramsey_angle_hz": float(ramsey_angle_hz),
            "used_double_frequency": False,
            "weak_component": None,
            "detuning_warning": abs(detuning_hz) > 10_000.0,
            "r_squared": _r_squared(y, fitted),
            "parameters": [float(value) for value in params],
            "fit_x": plot_x,
            "fit_response": plot_response,
        }

    single_fit_candidates: list[tuple[float, np.ndarray, np.ndarray]] = []
    for frequency_guess in _frequency_guesses(x, y, ramsey_angle_hz=ramsey_angle_hz):
        for phase_guess in (0.0, 0.5 * np.pi, -0.5 * np.pi, np.pi):
            try:
                candidate_params, _ = curve_fit(
                    ramsey_single_frequency_model,
                    x,
                    y,
                    p0=(float(np.mean(y)), 0.5 * span, frequency_guess, phase_guess, decay_guess),
                    bounds=(
                        (float(np.min(y) - span), -2.0 * span, -frequency_bound_hz, -2.0 * np.pi, min_decay_rate),
                        (float(np.max(y) + span), 2.0 * span, frequency_bound_hz, 2.0 * np.pi, max_decay_rate),
                    ),
                    maxfev=30_000,
                )
            except (RuntimeError, ValueError):
                continue
            candidate_fitted = ramsey_single_frequency_model(x, *candidate_params)
            residual_sum = float(np.sum((y - candidate_fitted) ** 2))
            single_fit_candidates.append((residual_sum, candidate_params, candidate_fitted))
    if not single_fit_candidates:
        raise ValueError("Ramsey 拟合失败，请检查 waiting time 范围和 I 分量数据。")
    _, single_params, single_fitted = min(single_fit_candidates, key=lambda item: item[0])
    single_params = _positive_frequency_params(single_params, frequency_indices=(2,), phase_indices=(3,))
    single_fitted = ramsey_single_frequency_model(x, *single_params)
    single_r_squared = _r_squared(y, single_fitted)
    params = single_params
    fitted = single_fitted
    model = "Single-frequency damped sine"
    detuning_hz: float | list[float] = float(single_params[2] - ramsey_angle_hz)
    t2_s: float | list[float] = float(1.0 / single_params[4])
    used_double_frequency = False
    weak_component: str | None = None
    if single_r_squared <= 0.9:
        try:
            double_params, _ = curve_fit(
                ramsey_double_frequency_model,
                x,
                y,
                p0=(
                    float(single_params[0]),
                    float(single_params[1]),
                    float(single_params[2]),
                    float(single_params[3]),
                    float(single_params[4]),
                    0.25 * span,
                    float(-single_params[2] if abs(single_params[2]) > np.finfo(float).eps else ramsey_angle_hz),
                    0.0,
                    float(single_params[4]),
                ),
                bounds=(
                    (float(np.min(y) - span), -2.0 * span, -frequency_bound_hz, -2.0 * np.pi, min_decay_rate, -2.0 * span, -frequency_bound_hz, -2.0 * np.pi, min_decay_rate),
                    (float(np.max(y) + span), 2.0 * span, frequency_bound_hz, 2.0 * np.pi, max_decay_rate, 2.0 * span, frequency_bound_hz, 2.0 * np.pi, max_decay_rate),
                ),
                maxfev=60_000,
            )
            double_fitted = ramsey_double_frequency_model(x, *double_params)
            double_r_squared = _r_squared(y, double_fitted)
            if double_r_squared > single_r_squared:
                double_params = _positive_frequency_params(double_params, frequency_indices=(2, 6), phase_indices=(3, 7))
                double_fitted = ramsey_double_frequency_model(x, *double_params)
                params = double_params
                fitted = double_fitted
                model = "Double-frequency damped sine"
                used_double_frequency = True
                detuning_hz = [float(double_params[2] - ramsey_angle_hz), float(double_params[6] - ramsey_angle_hz)]
                t2_s = [float(1.0 / double_params[4]), float(1.0 / double_params[8])]
                weaker_index = 0 if abs(double_params[1]) <= abs(double_params[5]) else 1
                weak_component = f"param({2 if weaker_index == 0 else 6})"
        except (RuntimeError, ValueError):
            pass
    r_squared = _r_squared(y, fitted)
    plot_x = np.linspace(float(x[0]), float(x[-1]), max(800, int(x.size * 20)))
    plot_response = (
        ramsey_double_frequency_model(plot_x, *params)
        if used_double_frequency
        else ramsey_single_frequency_model(plot_x, *params)
    )
    return {
        "model": model,
        "t2_s": t2_s,
        "detuning_hz": detuning_hz,
        "ramsey_angle_hz": float(ramsey_angle_hz),
        "used_double_frequency": used_double_frequency,
        "weak_component": weak_component,
        "detuning_warning": _max_abs(detuning_hz) > 10_000.0,
        "r_squared": r_squared,
        "parameters": [float(value) for value in params],
        "fit_x": plot_x,
        "fit_response": plot_response,
    }


def analyze_single_shot(raw: RawResult) -> dict[str, object]:
    labels = raw.metadata.get("state_labels")
    if not isinstance(labels, list) or len(labels) != raw.i_values.size:
        raise ValueError("Single Shot 需要 metadata.state_labels 标记 g/e 散点。")
    g_mask = np.asarray([label == "g" for label in labels], dtype=bool)
    e_mask = np.asarray([label == "e" for label in labels], dtype=bool)
    if not np.any(g_mask) or not np.any(e_mask):
        raise ValueError("Single Shot 需要同时包含 g/e 两组散点。")

    g_i = raw.i_values[g_mask]
    g_q = raw.q_values[g_mask]
    e_i = raw.i_values[e_mask]
    e_q = raw.q_values[e_mask]
    g_center = np.array([np.nanmean(g_i), np.nanmean(g_q)])
    e_center = np.array([np.nanmean(e_i), np.nanmean(e_q)])

    # 二维高斯拟合：均值 + 协方差的 MLE，沿判别轴方向的方差 σ² = aᵀΣa。
    g_cov = np.cov(np.column_stack([g_i, g_q]), rowvar=False)
    e_cov = np.cov(np.column_stack([e_i, e_q]), rowvar=False)

    values = raw.i_values + 1j * raw.q_values
    origin = complex(g_center[0], g_center[1])
    axis = _discrimination_axis(origin, complex(e_center[0], e_center[1]))
    g_projection = _project_onto_axis(values[g_mask], origin, axis)
    e_projection = _project_onto_axis(values[e_mask], origin, axis)

    axis_vector = np.array([axis.real, axis.imag])
    g_sigma = float(np.sqrt(max(axis_vector @ g_cov @ axis_vector, np.finfo(float).eps)))
    e_sigma = float(np.sqrt(max(axis_vector @ e_cov @ axis_vector, np.finfo(float).eps)))
    fwhm_g = _fwhm(g_sigma)
    fwhm_e = _fwhm(e_sigma)

    separation = float(np.linalg.norm(e_center - g_center))
    threshold, _ = _best_threshold(g_projection, e_projection)
    g_correct = float(np.mean(g_projection < threshold))
    e_correct = float(np.mean(e_projection >= threshold))
    thermal = float(np.mean(g_projection >= threshold))

    bin_count = _single_shot_bin_count(raw.metadata.get("histogram_bins"))
    r2_g = _projection_gaussian_r2(g_projection, center=0.0, sigma=g_sigma, bins=bin_count)
    r2_e = _projection_gaussian_r2(e_projection, center=separation, sigma=e_sigma, bins=bin_count)

    r2_pass = bool(r2_g > 0.9 and r2_e > 0.9)
    rayleigh_pass = bool(separation > fwhm_g + fwhm_e)
    gg_ee_pass = bool(g_correct > 0.9 and e_correct > 0.9)

    return {
        "model": "2D Gaussian fit",
        "separation": separation,
        "fwhm_g": fwhm_g,
        "fwhm_e": fwhm_e,
        "r2_g": r2_g,
        "r2_e": r2_e,
        "r_squared": min(r2_g, r2_e),
        "r2_pass": r2_pass,
        "rayleigh_pass": rayleigh_pass,
        "gg_ee_pass": gg_ee_pass,
        "passed": r2_pass and rayleigh_pass and gg_ee_pass,
        "g_center_i": float(g_center[0]),
        "g_center_q": float(g_center[1]),
        "e_center_i": float(e_center[0]),
        "e_center_q": float(e_center[1]),
        "threshold": threshold,
        "g_correct": g_correct,
        "e_correct": e_correct,
        "thermal": thermal,
        "measuretime": raw.metadata.get("measuretime"),
        "readout_amp": raw.metadata.get("readout_amp"),
        "waiting": raw.metadata.get("waiting"),
        "projection_origin_i": float(origin.real),
        "projection_origin_q": float(origin.imag),
        "projection_axis_real": float(axis.real),
        "projection_axis_imag": float(axis.imag),
    }


def save_raw_csv(raw: RawResult, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([raw.sweep_name, "I", "Q", "A", "status"])
        for frequency, i_value, q_value, amplitude, status in zip(
            raw.sweep_values,
            raw.i_values,
            raw.q_values,
            raw.amplitudes,
            raw.point_status,
            strict=True,
        ):
            writer.writerow([frequency, i_value, q_value, amplitude, status])


def save_fit_plot(
    *,
    raw: RawResult,
    response: np.ndarray,
    fit: dict[str, object],
    title: str,
    x_label: str,
    y_label: str,
    x_scale: float,
    path: Path,
    data_label: str = "experiment data",
    center_label: str = "fit center",
    expected_x: float | None = None,
    expected_label: str | None = None,
) -> None:
    frequencies = np.asarray(fit["fit_frequencies_hz"], dtype=float)
    fitted = np.asarray(fit["fit_response"], dtype=float)
    finite = np.isfinite(raw.sweep_values) & np.isfinite(response)
    figure, axis = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    axis.scatter(raw.sweep_values[finite] / x_scale, response[finite], s=20, label=data_label)
    axis.plot(frequencies / x_scale, fitted, color="red", label="Lorentzian fit")
    axis.axvline(float(fit["center_hz"]) / x_scale, linestyle="--", color="black", label=center_label)
    if expected_x is not None:
        axis.axvline(
            expected_x / x_scale,
            linestyle="-.",
            color="teal",
            label=expected_label or "expected",
        )
    axis.set_title(title)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.grid(alpha=0.25)
    axis.legend()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_xy_fit_plot(
    *,
    raw: RawResult,
    response: np.ndarray,
    fit: dict[str, object],
    title: str,
    x_label: str,
    y_label: str,
    x_scale: float,
    path: Path,
    annotation: str | None = None,
) -> None:
    x = np.asarray(fit["fit_x"], dtype=float)
    fitted = np.asarray(fit["fit_response"], dtype=float)
    finite = np.isfinite(raw.sweep_values) & np.isfinite(response)
    figure, axis = plt.subplots(figsize=(8.0, 5.0), constrained_layout=True)
    axis.scatter(raw.sweep_values[finite] / x_scale, response[finite], s=20, label="experiment data")
    axis.plot(x / x_scale, fitted, color="red", label=f"{fit['model']} fit")
    axis.set_title(title)
    axis.set_xlabel(x_label)
    axis.set_ylabel(y_label)
    axis.grid(alpha=0.25)
    if annotation:
        axis.text(
            0.52,
            0.62,
            annotation,
            transform=axis.transAxes,
            fontsize=12,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "none", "alpha": 0.75},
        )
    axis.legend()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_power_rabi_plot(
    *,
    raw: RawResult,
    response: np.ndarray,
    fit: dict[str, object],
    q_fit: dict[str, object] | None,
    title: str,
    path: Path,
) -> None:
    x = np.asarray(fit["fit_x"], dtype=float)
    fitted = np.asarray(fit["fit_response"], dtype=float)
    finite = np.isfinite(raw.sweep_values) & np.isfinite(response) & np.isfinite(raw.q_values)
    figure, axes = plt.subplots(1, 3, figsize=(15.0, 4.8), constrained_layout=True)
    axes[0].scatter(raw.sweep_values[finite], raw.i_values[finite], s=20, color="tab:blue", label="I data")
    axes[0].plot(x, fitted, color="navy", label="I fit")
    axes[0].set_title(f"{title}: amp vs I")
    axes[0].set_xlabel(PLOT_AXES_BY_EXPERIMENT["PowerRabi"][0])
    axes[0].set_ylabel(PLOT_AXES_BY_EXPERIMENT["PowerRabi"][1])
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    axes[1].scatter(raw.sweep_values[finite], raw.q_values[finite], s=20, color="tab:orange", label="Q data")
    if q_fit is not None:
        q_x = np.asarray(q_fit["fit_x"], dtype=float)
        q_fitted = np.asarray(q_fit["fit_response"], dtype=float)
        axes[1].plot(q_x, q_fitted, color="darkorange", label="Q fit")
    axes[1].set_title(f"{title}: amp vs Q")
    axes[1].set_xlabel(PLOT_AXES_BY_EXPERIMENT["PowerRabiQ"][0])
    axes[1].set_ylabel(PLOT_AXES_BY_EXPERIMENT["PowerRabiQ"][1])
    axes[1].grid(alpha=0.25)
    axes[1].legend()

    scatter = axes[2].scatter(raw.i_values[finite], raw.q_values[finite], c=raw.sweep_values[finite], cmap="viridis", s=24)
    axes[2].set_xlabel(PLOT_AXES_BY_EXPERIMENT["PowerRabiIQ"][0])
    axes[2].set_ylabel(PLOT_AXES_BY_EXPERIMENT["PowerRabiIQ"][1])
    axes[2].set_title(f"{title}: I vs Q")
    axes[2].grid(alpha=0.25)
    colorbar = figure.colorbar(scatter, ax=axes[2])
    colorbar.set_label("amp")
    figure.savefig(path, dpi=150)
    plt.close(figure)


def save_single_shot_plot(*, raw: RawResult, analysis: dict[str, object], title: str, path: Path) -> None:
    labels = raw.metadata.get("state_labels")
    g_mask = np.asarray([label == "g" for label in labels], dtype=bool)
    e_mask = np.asarray([label == "e" for label in labels], dtype=bool)
    figure, axes = plt.subplots(2, 2, figsize=(12.0, 8.5), constrained_layout=True)
    figure.suptitle(title)
    rotated_i, rotated_q = _single_shot_rotated_iq(raw.i_values, raw.q_values, analysis)
    _plot_single_shot_scatter(axes[0, 0], rotated_i, rotated_q, g_mask, e_mask, title="I1")
    i2_values = _scaled_axis(rotated_i)
    q2_values = _scaled_axis(rotated_q)
    _plot_single_shot_scatter(axes[0, 1], i2_values, q2_values, g_mask, e_mask, title="I2")
    bins = raw.metadata.get("histogram_bins")
    projection_scale = _axis_scale(rotated_i)
    _plot_single_shot_histogram(axes[1, 0], rotated_i, g_mask, e_mask, analysis=analysis, bins=bins, scale=1.0)
    _plot_single_shot_histogram(axes[1, 1], rotated_i / projection_scale, g_mask, e_mask, analysis=analysis, bins=bins, scale=projection_scale)
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _finite_xy(x_values: np.ndarray, y_values: np.ndarray, *, minimum: int, label: str) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x_values, dtype=float)
    y = np.asarray(y_values, dtype=float)
    finite = np.isfinite(x) & np.isfinite(y)
    x = x[finite]
    y = y[finite]
    if x.size < minimum or np.any(np.diff(x) <= 0.0):
        raise ValueError(f"{label} 拟合至少需要 {minimum} 个严格递增的有效点。")
    return x, y


def _r_squared(observed: np.ndarray, fitted: np.ndarray) -> float:
    total = float(np.sum((observed - np.mean(observed)) ** 2))
    return 1.0 - float(np.sum((observed - fitted) ** 2)) / total if total else 0.0


def _max_abs(value: float | list[float]) -> float:
    values = np.asarray(value if isinstance(value, list) else [value], dtype=float)
    return float(np.max(np.abs(values)))


def _frequency_guesses(x: np.ndarray, y: np.ndarray, *, ramsey_angle_hz: float) -> list[float]:
    guesses = [float(ramsey_angle_hz), -float(ramsey_angle_hz)]
    if x.size >= 4:
        dt = float(np.median(np.diff(x)))
        if dt > 0.0:
            centered = y - np.mean(y)
            spectrum = np.fft.rfft(centered)
            frequencies = np.fft.rfftfreq(centered.size, dt)
            if frequencies.size > 1:
                index = int(np.argmax(np.abs(spectrum[1:])) + 1)
                fft_guess = float(frequencies[index])
                guesses.extend([fft_guess, -fft_guess])
    unique: list[float] = []
    for guess in guesses:
        if abs(guess) < np.finfo(float).eps:
            continue
        if not any(abs(guess - existing) < 1.0 for existing in unique):
            unique.append(guess)
    return unique or [1.0 / max(float(np.ptp(x)), np.finfo(float).eps)]


def _positive_frequency_params(params: np.ndarray, *, frequency_indices: tuple[int, ...], phase_indices: tuple[int, ...]) -> np.ndarray:
    normalized = np.array(params, dtype=float, copy=True)
    for frequency_index, phase_index in zip(frequency_indices, phase_indices):
        if normalized[frequency_index] < 0.0:
            normalized[frequency_index] = -normalized[frequency_index]
            normalized[phase_index] = np.pi - normalized[phase_index]
    return normalized


def _discrimination_axis(ground_center: complex, excited_center: complex) -> complex:
    vector = excited_center - ground_center
    if abs(vector) == 0.0:
        raise ValueError("g/e 两个 single-shot 中心重合，无法判别。")
    return vector / abs(vector)


def _project_onto_axis(values: np.ndarray, origin: complex, axis: complex) -> np.ndarray:
    return np.real((values - origin) * np.conjugate(axis))


def _best_threshold(ground_projection: np.ndarray, excited_projection: np.ndarray) -> tuple[float, float]:
    lower = float(min(np.min(ground_projection), np.min(excited_projection)))
    upper = float(max(np.max(ground_projection), np.max(excited_projection)))
    candidates = np.linspace(lower, upper, 1000)
    best_fidelity = -1.0
    best_cut = float(candidates[0])
    for threshold in candidates:
        p_ground_correct = np.mean(ground_projection < threshold)
        p_excited_correct = np.mean(excited_projection >= threshold)
        fidelity = 0.5 * (p_ground_correct + p_excited_correct)
        if fidelity > best_fidelity:
            best_fidelity = float(fidelity)
            best_cut = float(threshold)
    return best_cut, best_fidelity


def _fwhm(sigma: float) -> float:
    """高斯半高全宽 FWHM = 2√(2·ln2)·σ ≈ 2.3548σ。"""
    return float(2.0 * np.sqrt(2.0 * np.log(2.0)) * float(sigma))


def _gaussian_pdf(x: np.ndarray, center: float, sigma: float) -> np.ndarray:
    return np.exp(-0.5 * ((x - center) / sigma) ** 2) / (sigma * np.sqrt(2.0 * np.pi))


def _single_shot_bin_count(bins: object) -> int:
    return int(bins) if isinstance(bins, (int, float)) and int(bins) > 1 else 80


def _projection_gaussian_r2(
    projection: np.ndarray,
    *,
    center: float,
    sigma: float,
    bins: int,
) -> float:
    """在判别轴投影直方图上，用二维高斯的边际 N(center, σ²) 作模型计算 R²。"""
    values = np.asarray(projection, dtype=float)
    if values.size < 2 or float(np.ptp(values)) <= np.finfo(float).eps:
        return 0.0
    sigma = max(float(sigma), np.finfo(float).eps)
    edges = np.linspace(float(np.min(values)), float(np.max(values)), bins)
    counts, edges = np.histogram(values, bins=edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(np.diff(edges)[0])
    fitted = values.size * width * _gaussian_pdf(centers, center, sigma)
    ss_res = float(np.sum((counts - fitted) ** 2))
    ss_tot = float(np.sum((counts - np.mean(counts)) ** 2))
    return 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0


def _plot_single_shot_scatter(axis, i_values: np.ndarray, q_values: np.ndarray, g_mask: np.ndarray, e_mask: np.ndarray, *, title: str) -> None:
    axis.scatter(i_values[g_mask], q_values[g_mask], s=4, alpha=0.65, label="g")
    axis.scatter(i_values[e_mask], q_values[e_mask], s=4, alpha=0.65, label="e")
    axis.set_title(title)
    axis.set_xlabel("I")
    axis.set_ylabel("Q")
    _set_padded_limits(axis, i_values, q_values)
    axis.grid(alpha=0.18)
    axis.legend(loc="upper right")


def _plot_single_shot_histogram(
    axis,
    i_values: np.ndarray,
    g_mask: np.ndarray,
    e_mask: np.ndarray,
    *,
    analysis: dict[str, object],
    bins: object = None,
    scale: float = 1.0,
) -> None:
    bin_count = _single_shot_bin_count(bins)
    edges = np.linspace(float(np.min(i_values)), float(np.max(i_values)), bin_count)
    g_counts, edges = np.histogram(i_values[g_mask], bins=edges)
    e_counts, _ = np.histogram(i_values[e_mask], bins=edges)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(np.diff(edges)[0])
    axis.bar(centers, g_counts, width=width, color="tab:blue", alpha=0.7, label="g")
    axis.bar(centers, e_counts, width=width, color="tab:orange", alpha=0.7, label="e")
    threshold = float(analysis["threshold"]) / scale
    axis.axvline(threshold, color="black", linewidth=1.2, label="threshold")
    axis.set_xlabel("I")
    axis.set_ylabel("count")
    axis.grid(alpha=0.18)
    axis.legend(loc="upper right")
    info = "\n".join(
        [
            f"threshold= {threshold:.4g}",
            f"gg= {float(analysis['g_correct']):.5f}",
            f"ee= {float(analysis['e_correct']):.5f}",
        ]
    )
    axis.text(0.55, 0.92, info, transform=axis.transAxes, va="top", fontsize=9)


def _axis_scale(values: np.ndarray) -> float:
    span = max(float(np.ptp(values)), np.finfo(float).eps)
    return max(span / 150.0, 1.0)


def _scaled_axis(values: np.ndarray) -> np.ndarray:
    return values / _axis_scale(values)


def _single_shot_rotated_iq(i_values: np.ndarray, q_values: np.ndarray, analysis: dict[str, object]) -> tuple[np.ndarray, np.ndarray]:
    origin = complex(float(analysis["projection_origin_i"]), float(analysis["projection_origin_q"]))
    axis = complex(float(analysis["projection_axis_real"]), float(analysis["projection_axis_imag"]))
    values = i_values + 1j * q_values
    rotated = (values - origin) * np.conjugate(axis)
    return np.real(rotated), np.imag(rotated)


def _set_padded_limits(axis, x_values: np.ndarray, y_values: np.ndarray) -> None:
    x_span = max(float(np.ptp(x_values)), 1.0)
    y_span = max(float(np.ptp(y_values)), 1.0)
    axis.set_xlim(float(np.min(x_values) - 0.08 * x_span), float(np.max(x_values) + 0.08 * x_span))
    axis.set_ylim(float(np.min(y_values) - 0.08 * y_span), float(np.max(y_values) + 0.08 * y_span))
