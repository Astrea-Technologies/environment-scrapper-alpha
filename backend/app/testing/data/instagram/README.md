# Instagram Test Data

This directory contains sample APIFY response data for testing the Instagram collector functionality.

## Sample Files

1. **profile_samples.json** - Contains sample Instagram profile data from APIFY
2. **post_samples.json** - Contains sample Instagram post data from APIFY
3. **comment_samples.json** - Contains sample Instagram comment data from APIFY

## Current Structure

The files currently contain placeholder data that resembles the structure of real APIFY responses. You should replace this placeholder data with actual APIFY responses for accurate testing.

## How to Capture Real APIFY Responses

A utility script `capture_apify_responses.py` is provided to help you capture real APIFY responses:

### Capturing Profile Data

```bash
python capture_apify_responses.py profile <instagram_username>
```

### Capturing Post Data

```bash
python capture_apify_responses.py posts <instagram_username> --count 10
```

### Capturing Comment Data

```bash
python capture_apify_responses.py comments <instagram_post_url> --count 20
```

## Manual Capture

You can also manually capture APIFY responses:

1. Go to the [APIFY Console](https://console.apify.com/)
2. Run the appropriate actor:
   - For profiles and posts: `vdrmota/instagram-scraper` (Actor ID: `cL9BqLGM9fymiF8rs`)
   - For comments: `apify/instagram-comment-scraper`
3. Save the response data to the appropriate file

## Using the Captured Data

After capturing real APIFY responses, you can run the Instagram test collector to verify that the data is correctly transformed:

```bash
# From the project root
python -m app.testing.collectors.run_instagram_test --workflow <username> <post_count>
```

This will simulate the entire Instagram scraping workflow using your captured data. 