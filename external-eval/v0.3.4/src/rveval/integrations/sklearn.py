"""Real offline datasets, sklearn estimator execution and native accuracy_score.

These are development integrations, not an LLM/VERITAS uplift study. Training
labels stay with the training component. Held-out labels are read only by scorer.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from dataclasses import dataclass
from rveval.interfaces import BenchmarkAdapter, BenchmarkSession, DeferredScore, Agent
from rveval.models import CandidateAction, Observation
from rveval.canonical import sha_json
from rveval.guardrails import require


def data_and_split(config):
    from sklearn import datasets
    from sklearn.model_selection import train_test_split
    import numpy as np
    name = config.get('dataset', 'iris')
    require(name in {'iris', 'wine', 'digits'}, 'SKLEARN_DATASET_NOT_BUNDLED')
    data = getattr(datasets, 'load_' + name)()
    indices = np.arange(len(data.target))
    train, test = train_test_split(indices, test_size=config.get('test_size', .25),
                                  random_state=config.get('split_seed', 29), stratify=data.target)
    return data, train, test


class Score(DeferredScore):
    def __init__(self, state):
        self.state = deepcopy(state)
        self.label, self.prediction, self.completed = self.state['scoring_data']['target'], self.state['prediction'], self.state['done']
    def fingerprint(self):
        return sha_json(self.state)
    def score(self):
        from sklearn.metrics import accuracy_score
        if not self.state['done']:
            return {'status': 'ABSTAINED', 'count': 1, 'correct': 0, 'native_accuracy': None}
        accuracy = float(accuracy_score([self.state['scoring_data']['target']], [self.state['prediction']]))
        return {'status': 'SCORED', 'count': 1, 'correct': int(accuracy), 'native_accuracy': accuracy}


class Session(BenchmarkSession):
    def __init__(self, x, label, classes):
        self.x, self._label, self.classes = x.tolist(), int(label), classes
        self.answer, self.done = None, False
    def task_payload(self): return {'features': deepcopy(self.x), 'classes': self.classes}
    def agent_state(self): return {'prediction_submitted': self.done}
    def pairing_state(self): return {'features': self.x, 'prediction': self.answer, 'done': self.done, 'scoring_data': {'target': self._label}}
    def tool_schema(self): return []
    def apply(self, candidate):
        require(not self.done, 'CLASSIFICATION_ALREADY_COMPLETED')
        require(candidate.kind == 'final_answer' and type(candidate.content) is int,
                'CLASSIFICATION_INTEGER_PREDICTION_REQUIRED')
        require(candidate.content in self.classes, 'CLASSIFICATION_UNKNOWN_CLASS')
        self.answer, self.done = candidate.content, True
        return Observation('prediction_recorded', {'prediction': self.answer}, True)
    def is_terminal(self): return self.done
    def native_score(self): return self.defer_score().score()
    def defer_score(self): return Score(self.pairing_state())


class SklearnAdapter(BenchmarkAdapter):
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        self.data, self.train, self.test = data_and_split(config)
        self.lookup = {'example_' + str(i): int(row) for i, row in enumerate(self.test)}
        self.classes = sorted(set(self.data.target.tolist()))
    def identity(self):
        import sklearn
        return {'benchmark': 'sklearn-bundled-' + self.config.get('dataset', 'iris'),
                'sklearn_version': sklearn.__version__, 'config': self.config,
                'data_sha256': sha_json({'features': self.data.data.tolist(), 'labels': self.data.target.tolist()}),
                'train_indices_sha256': sha_json(self.train.tolist()), 'test_indices_sha256': sha_json(self.test.tolist()),
                'scorer': 'sklearn.metrics.accuracy_score', 'evaluation_class': 'EXTERNAL_DATASET_DEVELOPMENT'}
    def case_ids(self): return list(self.lookup)
    def case_fingerprint(self, case_id):
        i = self.lookup[case_id]
        return sha_json({'x': self.data.data[i].tolist(), 'label': int(self.data.target[i])})
    def open_session(self, case_id, *, seed, arm):
        i = self.lookup[case_id]
        return Session(self.data.data[i], self.data.target[i], self.classes)
    def compare_native_scores(self, a, b):
        av, bv = a.get('native_accuracy'), b.get('native_accuracy')
        return {'native_accuracy_delta': bv-av if av is not None and bv is not None else None,
                'a_status': a['status'], 'b_status': b['status']}
    def aggregate_native_scores(self, cases):
        out = {}
        for key in ('arm_a', 'arm_b'):
            scores = [(c.get(key) or {}).get('native_score') for c in cases]
            scores = [s for s in scores if s is not None]
            n = len(scores)
            out[key] = {'enrolled_valid': n, 'scored': sum(s['status']=='SCORED' for s in scores),
                        'correct': sum(s['correct'] for s in scores),
                        'accuracy_with_abstentions_in_denominator': sum(s['correct'] for s in scores)/n if n else None}
        return out


_MODEL_CACHE = {}
class SklearnAgent(Agent):
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression
        data, train, test = data_and_split(config)
        key = sha_json(config)
        if key not in _MODEL_CACHE:
            model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=29))
            model.fit(data.data[train], data.target[train])
            _MODEL_CACHE[key] = model
        self.model = _MODEL_CACHE[key]
        estimator = self.model[-1]
        self.model_hash = sha_json({'coef': estimator.coef_.tolist(), 'intercept': estimator.intercept_.tolist(),
                                   'scale': self.model[0].scale_.tolist(), 'mean': self.model[0].mean_.tolist(),
                                   'training_rows': train.tolist()})
    def identity(self):
        import sklearn
        return {'model': 'sklearn.StandardScaler+LogisticRegression', 'version': sklearn.__version__,
                'configuration': self.config, 'model_state_sha256': self.model_hash,
                'training': 'TRAIN_SPLIT_ONLY', 'provider_calls': 0}
    def reset(self, **kwargs): pass
    def act(self, *, task, history, state, tools):
        prediction = int(self.model.predict([task['features']])[0])
        return CandidateAction('final_answer', content=prediction)
