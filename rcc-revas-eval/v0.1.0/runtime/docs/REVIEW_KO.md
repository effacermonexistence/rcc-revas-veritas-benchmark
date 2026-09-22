# RCC/REVAS 0.1.0 로컬 canonical 실행본

이 버전은 타케시에게 전달할 **우리 쪽 bounded RCC/REVAS executable**을 고정한 것이다.
실제 Git commit은 배포 패키지의 `CANONICAL_PIN.json`, 실행 진입점은
`python -m rcc_revas_eval evaluate`다. GitHub 업로드나 메일 발송은 하지 않았다.

rc2의 F01–F07 결함을 코드에서 수정하고 회귀 테스트에 넣었다. 공식 36개 원본은
114,884바이트 전체 Git blob 해시를 대조한 뒤 그대로 포함했다. 변환 과정의
누락·임의 기본값·정답 키 전달·실행 후 채점표 변경·float 응답 오류·echo 승격·
중간 HTTP 실패 시 기록 유실을 각각 검사한다.

34개 개발 fixture와 36개 공식 fixture를 모두 실제 실행·재실행한다. 원래 partner
label과 우리 upstream HOLD/REJECT 의미가 다른 세 케이스는 보고서에 남긴다.
숫자를 맞추려고 원본 라벨이나 기준을 바꾸지 않았다.

160개 테스트에는 실제 loopback HTTP 테스트가 포함된다. 그 서버는 명시적인
테스트 피어이며 VERITAS의 실제 서버가 아니다. 우리 canonical 실행본의 freeze와
타케시의 독립 확인, 양측 공동계약 freeze, native full-treatment 실행 결과는 별도다.
