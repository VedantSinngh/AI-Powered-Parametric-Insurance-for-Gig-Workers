$ErrorActionPreference = 'Stop'

$root = 'c:\Users\snehj\OneDrive\Desktop\GRIDGUARD_GUIDEWIRE\AI-Powered-Parametric-Insurance-for-Gig-Workers'
$backend = Join-Path $root 'backend'

$ts = Get-Date -Format 'yyyyMMddHHmmss'
$email = "demo_$ts@example.com"
$device = "DEMO-$ts"

$registerBody = @{ device_id=$device; email=$email; full_name='Demo Rider'; platform='other'; city='bengaluru' } | ConvertTo-Json
$register = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/auth/register' -ContentType 'application/json' -Body $registerBody

Set-Location $backend
$otpHash = (docker compose exec -T backend python -c "from app.utils.email_otp import hash_otp; print(hash_otp('123456'))").Trim()
$policyId = "policy-demo-$ts"
$utcNow = (Get-Date).ToUniversalTime()
$today = $utcNow.AddDays(-1).ToString('yyyy-MM-dd')
$weekEnd = $utcNow.AddDays(7).ToString('yyyy-MM-dd')
$otpSessionId = $register.otp_session_id
$partnerId = $register.partner_id

docker compose exec -T mongodb mongosh --quiet --eval "db.getSiblingDB('gridguard').otp_sessions.updateOne({_id:'$otpSessionId'},{`$set:{otp_hash:'$otpHash',attempts:0,verified:false}})" | Out-Null
docker compose exec -T mongodb mongosh --quiet --eval "db.getSiblingDB('gridguard').policies.updateOne({_id:'$policyId'},{`$set:{partner_id:'$partnerId',week_start:'$today',week_end:'$weekEnd',premium_amount:18,risk_score:0.42,status:'active',deducted_at:new Date(),created_at:new Date(),updated_at:new Date()}},{upsert:true})" | Out-Null

Set-Location $root
$verifyBody = @{ otp_session_id=$otpSessionId; otp_code='123456' } | ConvertTo-Json
$verify = Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/auth/verify-otp' -ContentType 'application/json' -Body $verifyBody
$token = $verify.access_token
$authHeaders = @{ Authorization = "Bearer $token" }
$internalHeaders = @{ 'X-Internal-Key'='dev-internal-key'; 'Content-Type'='application/json' }

$me = Invoke-RestMethod -Headers $authHeaders -Uri 'http://localhost:8000/auth/me'
$h3 = $me.partner.primary_zone_h3
$city = $me.partner.city

Set-Location $backend
docker compose exec -T mongodb mongosh --quiet --eval "db.getSiblingDB('gridguard').grid_events.updateMany({h3_cell:'$h3',resolved_at:null},{`$set:{resolved_at:new Date()}})" | Out-Null
Set-Location $root

$event1 = @{ h3_cell=$h3; city=$city; event_type='rainfall'; severity=1.0; raw_value=15; source_api='demo' } | ConvertTo-Json
$event2 = @{ h3_cell=$h3; city=$city; event_type='aqi'; severity=1.0; raw_value=300; source_api='demo' } | ConvertTo-Json
$ingest1 = Invoke-RestMethod -Method Post -Headers $internalHeaders -Uri 'http://localhost:8000/grid/events/ingest' -Body $event1
$ingest2 = Invoke-RestMethod -Method Post -Headers $internalHeaders -Uri 'http://localhost:8000/grid/events/ingest' -Body $event2

$trigger = Invoke-RestMethod -Method Post -Headers @{ 'X-Internal-Key'='dev-internal-key' } -Uri "http://localhost:8000/payouts/trigger?partner_id=$partnerId&grid_event_id=$($ingest2.event_id)&duration_hours=1"
$history = Invoke-RestMethod -Headers $authHeaders -Uri 'http://localhost:8000/payouts/my-history?limit=5'
$policyCurrent = Invoke-RestMethod -Headers $authHeaders -Uri 'http://localhost:8000/policies/current'
$policyHistory = Invoke-RestMethod -Headers $authHeaders -Uri 'http://localhost:8000/policies/history?limit=5'
$workability = Invoke-RestMethod -Headers $authHeaders -Uri "http://localhost:8000/grid/workability/$h3"
$cityMap = Invoke-RestMethod -Uri "http://localhost:8000/grid/workability/city/$city"

Set-Location $backend
docker compose exec -T mongodb mongosh --quiet --eval "db.getSiblingDB('gridguard').partners.updateOne({_id:'admin-smoke-demo'}, {`$set:{device_id:'DEV-SMOKE-ADMIN',full_name:'Admin Smoke Demo',email:'vedaantsinngh@gmail.com',upi_handle:null,primary_zone_h3:null,city:'bengaluru',platform:'other',risk_tier:'low',is_admin:true,is_active:true,mock_wallet_balance:100,onboarded_at:new Date(),created_at:new Date(),updated_at:new Date()}}, {upsert:true})" | Out-Null
$adminToken = (docker compose exec -T backend python -c "from app.utils.jwt_handler import create_access_token; print(create_access_token({'sub':'admin-smoke-demo'}))").Trim()
Set-Location $root
$adminHeaders = @{ Authorization = "Bearer $adminToken" }
$adminSummary = Invoke-RestMethod -Headers $adminHeaders -Uri 'http://localhost:8000/admin/analytics/summary'
$adminPartners = Invoke-RestMethod -Headers $adminHeaders -Uri 'http://localhost:8000/admin/partners?limit=5'
$adminPayouts = Invoke-RestMethod -Headers $adminHeaders -Uri 'http://localhost:8000/admin/payouts/recent?limit=5'
$adminFraud = Invoke-RestMethod -Headers $adminHeaders -Uri 'http://localhost:8000/fraud/flags?limit=5'

$pages = @('/login','/verify','/dashboard','/history','/map','/profile','/overview','/analytics','/partners','/payouts','/fraud','/admin-live-map')
$pageStatus = @{}
foreach ($page in $pages) {
  $pageStatus[$page] = (Invoke-WebRequest -UseBasicParsing -Uri ("http://localhost:3000" + $page)).StatusCode
}

Set-Location $backend
docker compose exec -T mongodb mongosh --quiet --eval "db.getSiblingDB('gridguard').partners.deleteOne({_id:'admin-smoke-demo'})" | Out-Null

$result = [ordered]@{
  demo_email = $email
  partner_id = $partnerId
  rider_flow = [ordered]@{
    register_ok = [bool]$register.partner_id
    verify_ok = [bool]$verify.access_token
    auth_me_ok = [bool]$me.partner.id
    policy_current_present = [bool]$policyCurrent.policy
    policy_history_total = $policyHistory.total
    ingest1_score = $ingest1.workability_score
    ingest1_triggered = $ingest1.payout_triggered
    ingest2_score = $ingest2.workability_score
    ingest2_triggered = $ingest2.payout_triggered
    payout_trigger_status = $trigger.status
    payout_trigger_reason = $trigger.reason
    payout_history_total = $history.total
    workability_status = $workability.status
    city_cells_total = $cityMap.total
  }
  admin_flow = [ordered]@{
    summary_ok = [bool]$adminSummary.active_partners
    partners_total = $adminPartners.total
    payouts_total = $adminPayouts.total
    fraud_total = $adminFraud.total
  }
  frontend_routes = $pageStatus
}

$result | ConvertTo-Json -Depth 8
