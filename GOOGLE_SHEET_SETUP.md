# Automatic class data collection with Google Sheets

Set this up once (about 5 minutes) and every student's results land in **your**
Google Sheet the moment they submit — no result codes, no copy-paste. The class
heatmap then loads straight from the sheet.

## What you'll end up with
- A Google Sheet named however you like, with a **Responses** tab that fills in automatically.
- A **student link** to share in Google Classroom. Anyone who opens it and finishes the test is logged.
- A **Load class data from Google Sheet** button in the test's analyzer that builds the heatmap with one click.

---

## Step 1 — Make the Sheet and add the script
1. Go to **sheets.new** (or open any Google Sheet you want to use). Give it a name.
2. Click **Extensions → Apps Script**. A code editor opens in a new tab.
3. Delete anything in the `Code.gs` file, then paste in the full contents of
   [`apps_script/Code.gs`](apps_script/Code.gs) from this project.
   *(The test also shows this same code with a "Copy the script" button — Teacher tools → Set up automatic collection.)*
4. Click the **Save** icon (💾).

## Step 2 — Deploy it as a Web app
1. In the Apps Script editor, click **Deploy → New deployment**.
2. Click the gear ⚙️ next to "Select type" and choose **Web app**.
3. Set:
   - **Description:** anything (e.g., "Env Sci collector")
   - **Execute as:** **Me**
   - **Who has access:** **Anyone**
4. Click **Deploy**. Google will ask you to **Authorize access** — approve it with your account.
   (You may see a "Google hasn't verified this app" screen — click **Advanced → Go to (your project)**. This is your own script.)
5. Copy the **Web app URL**. It ends in `/exec`. This is your endpoint.

## Step 3 — Connect the test to your Sheet
1. Open the test (`assessment.html` / your GitHub Pages link).
2. Go to **Teacher tools → Set up automatic collection**.
3. Paste the **Web app URL** and click **Save & make student link**.
4. Copy the generated **student link** (it has your endpoint built in) and post it in Google Classroom.
   Use the Form A link for the pre-test and the Form B link for the post-test.

## Step 4 — Give the test, then load the heatmap
1. Students open your link, take the test, and submit. Rows appear in your **Responses** tab automatically.
2. In the test, go to **Teacher tools → Class data analyzer → Load class data from Google Sheet**.
   The heatmap, reteaching groups, item analysis, and misconception frequencies build instantly.

---

## Notes
- **Your data stays in your Google account.** The script runs as you, in your Sheet.
- The result-code method still works as a backup — if a student's submission doesn't reach the sheet
  (e.g., a network hiccup), they still get a code you can paste in manually.
- **Pre vs. post:** the Form A and Form B links write to the same sheet; the analyzer separates them, so you can compare growth.
- **Re-deploying:** if you change the script later, use **Deploy → Manage deployments → Edit → Version: New version** so the same URL keeps working.
- **Privacy:** the student link contains your endpoint URL. Anyone with the link can submit a row, which is fine for a low-stakes classroom diagnostic. If you ever want to stop collection, delete the deployment (Deploy → Manage deployments → Archive).
