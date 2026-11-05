"""Walk-forward market forecasting sandbox. Forecasts never set valuation drivers."""

from datetime import date
from typing import Annotated, Callable, Literal
import numpy as np
from pydantic import Field, model_validator
from engine import Input, Evidence


class MarketBar(Input):
    date: date
    open: Annotated[float, Field(gt=0, le=1e12)]
    high: Annotated[float, Field(gt=0, le=1e12)]
    low: Annotated[float, Field(gt=0, le=1e12)]
    close: Annotated[float, Field(gt=0, le=1e12)]
    volume: Annotated[float, Field(ge=0, le=1e18)] = 0

    @model_validator(mode="after")
    def candle(self):
        if (
            self.low > min(self.open, self.close)
            or self.high < max(self.open, self.close)
            or self.low > self.high
        ):
            raise ValueError("OHLC candle bounds are inconsistent")
        return self


class ForecastExperiment(Input):
    bars: Annotated[list[MarketBar], Field(min_length=25, max_length=5000)]
    minimum_train: Annotated[int, Field(ge=20, le=2000)] = 60
    horizon: Annotated[int, Field(ge=1, le=20)] = 5
    model: Literal["random_walk", "drift", "ar1"] = "ar1"
    source: Evidence
    adjustment: Literal["unadjusted", "split_adjusted", "total_return_adjusted"]

    @model_validator(mode="after")
    def dates(self):
        if any(b.date <= a.date for a, b in zip(self.bars, self.bars[1:])):
            raise ValueError("Bars require unique ascending dates")
        if self.minimum_train + self.horizon > len(self.bars):
            raise ValueError("Insufficient observations for a holdout fold")
        if (len(self.bars) - self.minimum_train) // self.horizon > 500:
            raise ValueError(
                "Experiment exceeds 500 folds; increase horizon or training window"
            )
        return self


def baseline_forecast(history, horizon, model):
    closes = np.array([b.close for b in history])
    if model == "random_walk":
        return [float(closes[-1])] * horizon
    logs = np.log(closes)
    if model == "drift":
        return np.exp(
            logs[-1]
            + np.arange(1, horizon + 1) * (logs[-1] - logs[0]) / (len(logs) - 1)
        ).tolist()
    # Fit only this fold's past. Log-price AR(1); no future observations in normalization.
    x = np.column_stack([np.ones(len(logs) - 1), logs[:-1]])
    intercept, beta = np.linalg.lstsq(x, logs[1:], rcond=None)[0]
    pred = []
    last = logs[-1]
    for _ in range(horizon):
        last = float(intercept + beta * last)
        if not -50 < last < 50:
            raise ValueError("AR forecast diverged outside numerical range")
        pred.append(float(np.exp(last)))
    return pred


def evaluate_forecast(
    experiment: ForecastExperiment, predictor: Callable | None = None
):
    folds = []
    actual = []
    predicted = []
    naive = []
    direction = []
    for end in range(
        experiment.minimum_train,
        len(experiment.bars) - experiment.horizon + 1,
        experiment.horizon,
    ):
        train = experiment.bars[:end]
        test = experiment.bars[end : end + experiment.horizon]
        forecast = (
            predictor(tuple(train), tuple(b.date for b in test))
            if predictor
            else baseline_forecast(train, experiment.horizon, experiment.model)
        )
        arr = np.asarray(forecast, dtype=float)
        if (
            arr.shape != (experiment.horizon,)
            or not np.isfinite(arr).all()
            or (arr <= 0).any()
        ):
            raise ValueError(
                "Predictor must return one finite positive close per horizon date"
            )
        truth = [b.close for b in test]
        reference = [train[-1].close] * len(test)
        actual.extend(truth)
        predicted.extend(arr.tolist())
        naive.extend(reference)
        direction.extend(
            (
                np.sign(arr - train[-1].close)
                == np.sign(np.array(truth) - train[-1].close)
            ).tolist()
        )
        folds.append(
            dict(
                train_end=train[-1].date.isoformat(),
                forecast_dates=[b.date.isoformat() for b in test],
                actual=truth,
                predicted=arr.tolist(),
                random_walk=reference,
            )
        )
    error = np.array(predicted) - actual
    reference = np.array(naive) - actual
    mae = float(np.abs(error).mean())
    baseline = float(np.abs(reference).mean())
    return dict(
        model=experiment.model if predictor is None else "external_predictor",
        folds=folds,
        observations=len(actual),
        mae=mae,
        rmse=float(np.sqrt((error**2).mean())),
        random_walk_mae=baseline,
        mae_skill=1 - mae / baseline if baseline else None,
        direction_accuracy=float(np.mean(direction)),
        source=experiment.source,
        adjustment=experiment.adjustment,
        evaluation="Expanding training window; non-overlapping test folds; all forecast leads pooled. No trading-return or statistical-significance claim.",
        limitations="Historical revisions, corporate actions, survivorship and pretrained-model training overlap require separate checks. A walk-forward split cannot remove leakage already present in pretrained weights.",
    )


def kronos_callback(predictor, max_context=512):
    """Wrap an explicitly loaded upstream KronosPredictor; no imports/downloads at startup.

    The caller owns pinned model/tokenizer revisions, license checks, device and seed.
    No model is bundled and no LLM or neural inference runs unless this callback is used.
    """
    if not 2 <= max_context <= 2048:
        raise ValueError("Unsupported context length")

    def forecast(history, future_dates):
        import pandas as pd  # optional external runtime, not a base dependency

        frame = pd.DataFrame([b.model_dump() for b in history[-max_context:]])
        output = predictor.predict(
            df=frame[["open", "high", "low", "close", "volume"]],
            x_timestamp=pd.Series(pd.to_datetime(frame["date"])),
            y_timestamp=pd.Series(pd.to_datetime(list(future_dates))),
            pred_len=len(future_dates),
            T=1.0,
            top_p=0.9,
            sample_count=1,
            verbose=False,
        )
        if "close" not in output:
            raise ValueError("Kronos response has no close column")
        return output["close"].tolist()

    return forecast
