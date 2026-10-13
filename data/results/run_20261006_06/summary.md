# run_20261006_06 — P4 H3 stake models, second falsifier, Holm family

## Holm family
- H1 Tier (periphery) Salience: b = 0.103, CI [-0.148, 0.354], Holm p = 1.000, n = 52 → not supported
- H1 Tier (periphery) Framing: b = -0.010, CI [-0.065, 0.046], Holm p = 1.000, n = 52 → not supported
- H1 Tier (periphery) Timing: b = -0.026, CI [-0.132, 0.081], Holm p = 1.000, n = 37 → not supported
- H2 Wire reliance Salience: b = -0.020, CI [-0.267, 0.227], Holm p = 1.000, n = 52 → not supported
- H2 Wire reliance Framing: b = 0.019, CI [-0.066, 0.104], Holm p = 1.000, n = 52 → not supported
- H2 Wire reliance Timing: b = 0.175, CI [0.084, 0.267], Holm p = .002, n = 37 → supported
- H3 Periphery × stake Salience: b = 0.061, CI [-0.114, 0.236], Holm p = 1.000, n = 52 → not supported
- H3 Periphery × stake Framing: b = 0.019, CI [-0.032, 0.070], Holm p = 1.000, n = 52 → not supported
- H3 Periphery × stake Timing: b = 0.049, CI [-0.020, 0.117], Holm p = 1.000, n = 37 → not supported

## H3 and checks
- H3 tier × stake (linear 0/1/2) · Periphery × stake · Salience: b = 0.061, CI [-0.114, 0.236], p = .495, n = 52 — n = 52, var(country) = 0.0138, var(outlet) = 0.0095, residual = 0.0669
- H3 tier × stake (linear 0/1/2) · Stake (semi-periphery slope) · Salience: b = 0.083, CI [-0.041, 0.207], p = .192, n = 52 — 
- H3 tier × stake (linear 0/1/2) · Periphery (at stake 0) · Salience: b = 0.042, CI [-0.260, 0.344], p = .785, n = 52 — 
- H3 robustness: two dummy contrasts · Periphery × stake 1 (Gaza vs Ukraine) · Salience: b = 0.027, CI [-0.241, 0.295], p = .843, n = 52 — n = 52, var(country) = 0.0135, var(outlet) = 0.0174, residual = 0.0420
- H3 robustness: two dummy contrasts · Periphery × stake 2 (COP vs Ukraine) · Salience: b = 0.133, CI [-0.146, 0.412], p = .349, n = 52 — n = 52, var(country) = 0.0135, var(outlet) = 0.0174, residual = 0.0420
- H3 robustness: own-country share V10 in place of stake · Periphery × V10 · Salience: b = 2.510, CI [-0.916, 5.937], p = .151, n = 52 — n = 52, var(country) = 0.0307, var(outlet) = 0.0187, residual = 0.0594
- H3 robustness: own-country share V10 in place of stake · V10 (semi-periphery slope) · Salience: b = 1.023, CI [-0.291, 2.337], p = .127, n = 52 — 
- H3 tier × stake (linear 0/1/2) · Periphery × stake · Framing: b = 0.019, CI [-0.032, 0.070], p = .463, n = 52 — n = 52, var(outlet) = 0.0016, residual = 0.0057
- H3 tier × stake (linear 0/1/2) · Stake (semi-periphery slope) · Framing: b = -0.006, CI [-0.042, 0.030], p = .750, n = 52 — 
- H3 tier × stake (linear 0/1/2) · Periphery (at stake 0) · Framing: b = -0.028, CI [-0.102, 0.046], p = .457, n = 52 — 
- H3 main fit before dropping the zero-variance component · Periphery × stake · Framing: b = 0.019, CI [-0.033, 0.071], p = .470, n = 52 — n = 52, var(country) = 0.0000, var(outlet) = 0.0016, residual = 0.0057
- H3 tier × stake (linear 0/1/2) · Periphery × stake · Framing (without headline-only Post copies, X11): b = 0.026, CI [-0.032, 0.083], p = .385, n = 52 — n = 52, var(country) = 0.0001, var(outlet) = 0.0000, residual = 0.0073
- H3 tier × stake (linear 0/1/2) · Stake (semi-periphery slope) · Framing (without headline-only Post copies, X11): b = -0.005, CI [-0.046, 0.035], p = .795, n = 52 — 
- H3 tier × stake (linear 0/1/2) · Periphery (at stake 0) · Framing (without headline-only Post copies, X11): b = -0.029, CI [-0.103, 0.046], p = .447, n = 52 — 
- H3 robustness: two dummy contrasts · Periphery × stake 1 (Gaza vs Ukraine) · Framing: b = 0.052, CI [-0.060, 0.165], p = .364, n = 52 — n = 52, var(country) = 0.0002, var(outlet) = 0.0000, residual = 0.0074
- H3 robustness: two dummy contrasts · Periphery × stake 2 (COP vs Ukraine) · Framing: b = 0.036, CI [-0.080, 0.152], p = .545, n = 52 — n = 52, var(country) = 0.0002, var(outlet) = 0.0000, residual = 0.0074
- H3 robustness: own-country share V10 in place of stake · Periphery × V10 · Framing: b = -0.068, CI [-0.981, 0.846], p = .885, n = 52 — n = 52, var(outlet) = 0.0017, residual = 0.0053
- H3 robustness: own-country share V10 in place of stake · V10 (semi-periphery slope) · Framing: b = 0.323, CI [-0.048, 0.695], p = .088, n = 52 — 
- H3 tier × stake (linear 0/1/2) · Periphery × stake · Timing: b = 0.049, CI [-0.020, 0.117], p = .165, n = 37 — n = 37, var(country) = 0.0012, var(outlet) = 0.0064, residual = 0.0048
- H3 tier × stake (linear 0/1/2) · Stake (semi-periphery slope) · Timing: b = 0.007, CI [-0.039, 0.053], p = .779, n = 37 — 
- H3 tier × stake (linear 0/1/2) · Periphery (at stake 0) · Timing: b = -0.058, CI [-0.173, 0.057], p = .322, n = 37 — 
- H3 robustness: two dummy contrasts · Periphery × stake 1 (Gaza vs Ukraine) · Timing: b = 0.020, CI [-0.077, 0.117], p = .684, n = 37 — n = 37, var(country) = 0.0008, var(outlet) = 0.0068, residual = 0.0049
- H3 robustness: two dummy contrasts · Periphery × stake 2 (COP vs Ukraine) · Timing: b = 0.135, CI [-0.023, 0.293], p = .093, n = 37 — n = 37, var(country) = 0.0008, var(outlet) = 0.0068, residual = 0.0049
- H3 robustness: own-country share V10 in place of stake · Periphery × V10 · Timing: b = 0.092, CI [-1.731, 1.916], p = .921, n = 37 — n = 37, var(country) = 0.0020, var(outlet) = 0.0054, residual = 0.0059
- H3 robustness: own-country share V10 in place of stake · V10 (semi-periphery slope) · Timing: b = -0.099, CI [-0.861, 0.664], p = .800, n = 37 — 
- Second T1 falsifier: periphery following at high stake (COP) vs mismatched-issue benchmark · Mean following 0.64 vs benchmark -0.20 · Salience: b = 0.837, CI paired t(7) = 9.57, p = one-sided < .001, Holm < .001, n = 8 — falsifier does not hold (following above benchmark)
- Second T1 falsifier: periphery following at high stake (COP) vs mismatched-issue benchmark · Mean following -0.09 vs benchmark -0.12 · Framing: b = 0.025, CI paired t(7) = 1.31, p = one-sided .116, Holm .116, n = 8 — falsifier holds (following not above benchmark)
- Second T1 falsifier: periphery following at high stake (COP) vs mismatched-issue benchmark · Mean following 0.04 vs benchmark 0.04 · Timing: b = —, CI —, p = one-sided —, Holm —, n = 2 — not testable (too few cells)
- H3 check within the two wars with country × issue stake (A28) · — · All levels: b = —, CI —, p = —, n = — — dropped (X14): the country × issue stake code would have been hand-coded; nothing in the study is hand-coded
