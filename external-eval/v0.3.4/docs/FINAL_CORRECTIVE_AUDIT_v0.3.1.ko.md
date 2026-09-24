# v0.3.1 수정·재실행 결과

원본 native v0.3.0 commit `64982a1bcd22338de7389fa459b5beed2c82bf6e`에 새 반례 10개를 넣었고, 10개 모두 실패했다.

실행 직전 journal 동안 바뀐 상태를 놓치는 문제, 비동기 review의 잘못된 요청 연결,
NumPy 구조화 dtype 이름·offset 충돌, object scalar의 포인터 바이트 처리,
Decimal·complex·Fraction 입력, Torch 지연 conjugate view 문제를 고쳤다.
타케시의 네이티브 소스나 기존 테스트 기대값은 바꾸지 않았다.

수정 후 전체 코어·네이티브 테스트 **221개 통과, 실패·오류·건너뜀 0**.
새 반례 10개도 모두 통과했다. Iris·Wine·Digits의 **533개 held-out 예측 쌍**을
새로 실행했고, 세 구성 모두 COMPLETED 및 evidence 검증 PASS다.

그러나 ‘모든 벤치마크 실제 실행 + 전체 합의된 RCC/VERITAS 경로 완료’라는 기준은
아직 통과하지 않았다. 공식 SWE-bench Docker 채점, 모델 기반 전체 task/attack sweep,
전체 /v1/decide→TrustLog 경로는 이번 실행에 포함되지 않았다. 이것을 테스트 숫자로
대체하거나 최종 통과로 표시하지 않았다.

이 배포본은 발견한 결함을 수정하고 기존 네이티브 연결을 재검증한 v0.3.1이다.
원본 실패·수정 후 결과·실제 실행 로그는 audit_v031/에 보존한다.
