# Lightning NVIDIA NIM Pilot

Lightning is the manual-QA fallback when Modal cannot register an L40S
function. Lightning currently requires a verified payment method before a
free-tier account can start GPU compute. The persistent CPU Studio can store the
NIM image and cache; switch it to L40S only for scheduled QA sessions and stop
it immediately afterward.

The Studio runs two containers on a private Docker network:

- the pinned NVIDIA NIM, with no published port;
- the authenticated Go gateway, which alone publishes port 8080.

Required Studio environment variables are `NGC_API_KEY` and
`GATEWAY_BEARER_TOKEN`. Build `tools/nvidia-nim-gateway` as
`smart-mirror-nim-gateway:pilot`, expose port 8080 through Lightning, then run
`start.sh` after switching the Studio to L40S. Run `stop.sh`, then stop the
Studio; leaving a CPU Studio running is unnecessary for this workflow.

The free plan is suitable for short manual QA windows, not unattended visitor
traffic: free Studios restart periodically and GPU credits are finite.
