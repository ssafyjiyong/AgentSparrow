import sys, time
sys.path.insert(0, '.')

print('=== 포트 충돌 검사 테스트 ===')
start = time.time()
from agent.checks.ports import check_ports
result = check_ports()
elapsed = time.time() - start
print(f'결과: {result}')
print(f'소요 시간: {elapsed:.2f}초')
