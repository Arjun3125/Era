from ml.ml_orchestrator import MLWisdomOrchestrator

m = MLWisdomOrchestrator()
res = m.process_interaction('TEST','user says hi','program replies hello')
print('OK', isinstance(res, dict))
print(res)
