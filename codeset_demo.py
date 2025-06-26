import os
import time
import dotenv

from codeset import Codeset

dotenv.load_dotenv()

# Step 1. Initialize the client
print("Initializing Codeset client...")
start_time = time.time()
client = Codeset(
    api_key=os.getenv("CODESET_API_KEY"),
    base_url=os.getenv("CODESET_BASE_URL"),
    timeout=10*60, # TODO: The default should be higher
    max_retries=1, # TODO: The value should be default
)
elapsed = time.time() - start_time
print(f"Client initialized. (took {elapsed:.2f} seconds)")

# Step 2. Choose a sample
print("Listing samples...")
start_time = time.time()
response = client.samples.list()
elapsed = time.time() - start_time
print(f"Received {len(response)} samples. (took {elapsed:.2f} seconds)")
sample = response[0]
print(f"Selected sample: {sample}")

# Step 3. Start a session
print(f"Starting session for sample_id={sample.sample_id}...")
start_time = time.time()
session = client.sessions.create(
    sample_id=sample.sample_id,
)
elapsed = time.time() - start_time
print(f"Session started: {session} (took {elapsed:.2f} seconds)")

try:
    # Step 4. Run a command
    print(f"Running command for session_id={session.session_id}...")
    start_time = time.time()
    response = client.sessions.execute_command(
        session_id=session.session_id,
        command="pwd; ls -lah"
    )
    print(f"Command stdout:\n```\n{response.stdout}\n```")
    print(f"Command stderr:\n```\n{response.stderr}\n```")
    elapsed = time.time() - start_time
    print(f"Command executed. (took {elapsed:.2f} seconds)")

    # Step 5. Verify before making any changes
    print(f"Verifying before applying diff for session_id={session.session_id}...")
    start_time = time.time()
    job = client.sessions.verify.start(
        session_id=session.session_id
    )
    print(f"Verification started: {job}")

    # Step 6. Wait for verification to complete
    while True:
        result = client.sessions.verify.status(
            session_id=session.session_id,
            job_id=job.job_id
        )
        if result.status == "completed":
            break
        time.sleep(1)
    elapsed = time.time() - start_time
    print(f"Verification completed. (took {elapsed:.2f} seconds)")
    print(f"Verification result: {result}")

    # Step 7. Apply a diff
    print(f"Applying diff for session_id={session.session_id}...")
    start_time = time.time()
    response = client.sessions.apply_diff(
        session_id=session.session_id,
        diff="""diff --git a/src/main/java/org/traccar/protocol/Gt06ProtocolDecoder.java b/src/main/java/org/traccar/protocol/Gt06ProtocolDecoder.java
index d6d9884..4762fc8 100644
--- a/src/main/java/org/traccar/protocol/Gt06ProtocolDecoder.java
+++ b/src/main/java/org/traccar/protocol/Gt06ProtocolDecoder.java
@@ -836,11 +836,6 @@ public class Gt06ProtocolDecoder extends BaseProtocolDecoder {
                 }
             }
 
-            if (type == MSG_STATUS && variant == Variant.VXT01) {
-                position.set(Position.KEY_POWER, buf.readUnsignedShort() * 0.01);
-                position.set(Position.KEY_RSSI, buf.readUnsignedByte());
-            }
-
             if (type == MSG_GPS_LBS_1) {
                 if (variant == Variant.GT06E_CARD) {
                     position.set(Position.KEY_ODOMETER, buf.readUnsignedInt());
@@ -1421,8 +1416,6 @@ public class Gt06ProtocolDecoder extends BaseProtocolDecoder {
             variant = Variant.VXT01;
         } else if (header == 0x7878 && type == MSG_GPS_LBS_STATUS_1 && length == 0x24) {
             variant = Variant.VXT01;
-        } else if (header == 0x7878 && type == MSG_STATUS && length == 0x0a) {
-            variant = Variant.VXT01;
         } else if (header == 0x7878 && type == MSG_LBS_MULTIPLE_3 && length == 0x31) {
             variant = Variant.WANWAY_S20;
         } else if (header == 0x7878 && type == MSG_LBS_MULTIPLE_3 && length == 0x2e) {
"""
    )
    elapsed = time.time() - start_time
    print(f"Diff applied. (took {elapsed:.2f} seconds)")

    # Step 8. Verify after making changes
    print(f"Verifying after applying diff for session_id={session.session_id}...")
    start_time = time.time()
    job = client.sessions.verify.start(
        session_id=session.session_id
    )
    print(f"Verification started: {job}")

    # Step 9. Wait for verification to complete
    while True:
        result = client.sessions.verify.status(
            session_id=session.session_id,
            job_id=job.job_id
        )
        if result.status == "completed":
            break
        time.sleep(1)
    elapsed = time.time() - start_time
    print(f"Verification completed. (took {elapsed:.2f} seconds)")
    print(f"Verification result: {result}")

finally:
    # Step N. Close the session
    print(f"Closing session with session_id={session.session_id}...")
    start_time = time.time()
    client.sessions.close(session_id=session.session_id)
    elapsed = time.time() - start_time
    print(f"Session closed. (took {elapsed:.2f} seconds)")