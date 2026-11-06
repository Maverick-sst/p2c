# Twilio setup

## Before buying a number

Twilio does not currently offer local or mobile Indian phone numbers. Select a voice-enabled international number in a country/region supported by your account, then verify that your Indian mobile carrier can call it. International dialing/ISD may need to be enabled and charges may apply. A number being available in the Console does not guarantee reachability from every Indian carrier.

Do not buy a number until you have checked its Voice capability and confirmed the intended caller-to-number route with a small test.

## Configure the number

1. Create a Twilio account and verify the account as required.
2. In Phone Numbers, search for a number with Voice capability.
3. Open the number's Voice configuration.
4. Set "A call comes in" to Webhook.
5. Set the URL to your current public HTTPS tunnel URL followed by /voice.
6. Select HTTP POST and save.
7. Keep the tunnel URL synchronized with PUBLIC_BASE_URL in .env.

## Local development

Terminal 1:

    make install
    make run

Terminal 2:

    ngrok http 8000

Copy the HTTPS forwarding URL into .env as PUBLIC_BASE_URL, restart the app, then configure the same URL in Twilio.

## Test call

1. Call the Twilio number from the exact ALLOWED_PHONE number configured in .env.
2. Enter the six-digit ACCESS_PIN.
3. Press 1, 2, or 3.
4. Inspect the local FastAPI terminal for the task output.
5. Check Twilio's call logs and debugger if the call fails.

Twilio trial accounts may restrict verified caller/destination numbers and include trial announcements. Confirm current account restrictions in the Console.
