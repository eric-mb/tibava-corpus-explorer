# Prompt Log

Every prompt given to the AI coding assistant while building this project, in order.
Each step produces one commit.

---

## Step 1: Project setup

> I want to demonstrate vibe coding session by building corpus exploration tool for data produced by the video annotation platform tib av-analytics using streamlit.
>
> For this purpose, I want to document each prompt in a file and commit the resulting output of each step.
>
> I already added a folder with exported data for several videos exported from the tool.
>
> Please create the first commit including a readme file and another file that stores my user prompts.

## Step 2: Add exported data

> please commit the exports

## Step 3: Pattern search and statistics app

> Okay, now I want to create the app.
>
> It should have two views:
>
> View 1: A Pattern Search View where I can define a pattern like shot-reverse-shot as a python code block that can be executed to find the respective hits in a video. The results should be displayed on a timeline that shows the shot boundaries with a thumbnail of the shot above. Hits should be highlighted on the timeline with a color (different colors for A-B-A or C-B-C patterns) and when hovering over it one thumbnail per shot found in the sequence should be shown to investigate the pattern.
>
> View 2 should contain statistics for the camera sizes and the patterns defined in view 1 across the corpus.
>
> For now let's start with the first pattern which is shot-reverse-shot.
> It is defined as a sequence of shots where two persons appear in alternating order like A-B-A-B-A. it has to be at least of length 3 (no max length)

## Step 4: Push to GitHub

> push the code

## Step 5: All videos at once, timeline only

> Please list all videos at once in the pattern search instead of having them in a dropdown list.
> Also, please drop the table and the person in hits. The timeline with the thumbnails is enough.

## Step 6: Fit as default zoom

> Please let fit be the standarf for each timeline

## Step 7: Faces on screen

> Please create a new view where for each video a graph is created that shows the number of faces visible on screen.

## Step 8: Thumbnails for the faces view

> okay, please also add the thumbnails as in the pattern search view
