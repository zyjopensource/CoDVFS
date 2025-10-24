# -*- coding: utf-8 -*-
import numpy as np
import sklearn.gaussian_process as gp
from scipy.stats import norm
from scipy.optimize import minimize

def expected_improvement(x, gaussian_process, evaluated_loss, greater_is_better=False, n_params=1):
    x_to_predict = x.reshape(-1, n_params)
    mu, sigma = gaussian_process.predict(x_to_predict, return_std=True)
    loss_optimum = np.max(evaluated_loss) if greater_is_better else np.min(evaluated_loss)
    scaling_factor = (-1) ** (not greater_is_better)
    with np.errstate(divide='ignore'):
        Z = scaling_factor * (mu - loss_optimum) / sigma
        expected_improvement = scaling_factor * (mu - loss_optimum) * norm.cdf(Z) + sigma * norm.pdf(Z)
        expected_improvement[sigma == 0.0] == 0.0
    return -1 * expected_improvement

def sample_next_hyperparameter(acquisition_func, gaussian_process, evaluated_loss, greater_is_better=False,
                               bounds=(0, 10), n_restarts=25):
    best_x = None
    best_acquisition_value = 1
    n_params = bounds.shape[0]
    for starting_point in np.random.uniform(bounds[:, 0], bounds[:, 1], size=(n_restarts, n_params)):
        res = minimize(fun=acquisition_func, x0=starting_point.reshape(1, -1),
                       bounds=bounds, method='L-BFGS-B',
                       args=(gaussian_process, evaluated_loss, greater_is_better, n_params))
        if res.fun < best_acquisition_value:
            best_acquisition_value = res.fun
            best_x = res.x
    return best_x

def bayesian_optimisation(n_iters, sample_loss, bounds, x0=None, n_pre_samples=5,
                          gp_params=None, random_search=False, alpha=1e-5, epsilon=1e-7, paras=None):
    x_list, y_list = [], []
    n_params = bounds.shape[0]
    if x0 is None:
        for params in np.random.uniform(bounds[:, 0], bounds[:, 1], (n_pre_samples, bounds.shape[0])):
            x_list.append(params); y_list.append(sample_loss(params))
    else:
        for params in x0:
            x_list.append(params); y_list.append(sample_loss(params))
    xp = np.array(x_list); yp = np.array(y_list)
    model = gp.GaussianProcessRegressor(
        kernel=gp.kernels.Matern(), alpha=alpha, n_restarts_optimizer=10, normalize_y=True
    ) if gp_params is None else gp.GaussianProcessRegressor(**gp_params)

    for _ in range(n_iters):
        model.fit(xp, yp)
        if random_search:
            x_random = np.random.uniform(bounds[:, 0], bounds[:, 1], size=(random_search, n_params))
            ei = -1 * expected_improvement(x_random, model, yp, greater_is_better=True, n_params=n_params)
            next_sample = x_random[np.argmax(ei), :]
        else:
            next_sample = sample_next_hyperparameter(expected_improvement, model, yp,
                                                     greater_is_better=True, bounds=bounds, n_restarts=100)
        if paras is not None:
            # 将 next_sample 投影到合法频点集合（CPU 四舍五入到 0.1GHz；GPU 到最邻近的白名单）
            cpu = round(float(next_sample[0]), 1)
            # GPU：在合法频点列表中找最近的
            mindiff = 1e9; gpu = None
            for f in paras[1]:
                if abs(f - next_sample[1]) < mindiff:
                    gpu, mindiff = f, abs(f - next_sample[1])
            next_sample = np.array([cpu, gpu], dtype=float)
        else:
            # 避免重复采样
            pass

        cv_score = sample_loss(next_sample)
        x_list.append(next_sample); y_list.append(cv_score)
        xp = np.array(x_list); yp = np.array(y_list)
    return xp, yp
