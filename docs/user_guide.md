# User Guide

"I have a pipeline and I'm not afraid to use it!"

## Scenario

I have a Nextflow pipeline that I run by hand. Now I want it to run automatically whenever new sequencing data passes QC. I know the study, and input data will be stored in iRODS.

### Preliminaries

npg_porch is a RESTful OpenAPI service. Examples here are made with curl, but more complex logic is easier to implement with client libraries such as [REST::Client](https://metacpan.org/pod/REST::Client) or [requests](https://realpython.com/api-integration-in-python/)

The npg_porch server provides API documentation at $URL/redoc - it allows interactive use of the API.

However you choose to interact with npg_porch, it is particularly important to observe the server responses in order to identify errors in data, errors in server interaction or errors in networking. At the minimum you should stop if a response is not 200 - OK or 201 - CREATED

Bash tools like `jq` and `jo` can be useful in working with the server, as all messages use JSON format.

We have tried to make interactions with npg_porch as atomic as possible, so the data you send and the data you receive follow the same schema.

Security is necessary in order to prevent accidental misuse of npg_porch. An authorisation token can be provided to you by the maintainers, which you will then use to enable each non-GET request. Get requests do not require authorisation.

A note on HTTPS: Client libraries like `requests`, certain GUIs and Firefox will try to verify the server certificate authority. System-administered software are already configured correctly, but other packages installed by conda or pip may need to be told how the client may verify with a client certificate e.g. contained in `/usr/share/ca-certificates/`. It may also be useful to unset `https_proxy` and `HTTPS_PROXY` in your environment.

### Step 0 - get issued authorisation tokens

Access to the service is loosely controlled with authorisation tokens. You will be issued with an admin token that enables you to register pipelines, and further tokens for pipeline-specific communication. Please do not share the tokens around and use them for purposes besides the specific pipeline. This will help us to monitor pipeline reliability and quality of service. Authorisation is achieved by HTTP Bearer Token:

`curl -L -H "Authorization: Bearer $TOKEN" https://$SERVER:$PORT`

Authorisation tokens are specific to a pipeline and more than one token can be issued for a pipeline. New tokens for a pipeline can be obtained using the admin token, from the pipeline's token endpoint:

`curl -L -X POST -H "Authorization: Bearer $ADMIN_TOKEN" https://$SERVER:$PORT/pipelines/$PIPELINE_NAME/token/$TOKEN_DESCRIPTION`

The server will respond with a JSON document containing the new bearer token which you may use for subsequent pipeline-specific communication:

```javascript
{
    "name": "$PIPELINE_NAME",
    "description": "$TOKEN_DESCRIPTION",
    "token": "$TOKEN"
}
```

### Step 1 - register your pipeline with npg_porch

*Schema: npg_porch.model.pipeline*

Nothing in npg_porch can happen until there's a pipeline defined. For our purposes "pipeline" means "a thing you can run", and it may refer to specific code, or a wrapper that can run the pipeline in this particular way with some standard arguments.

You can name your pipeline however you like, but the name must be unique, and be as informative to you as possible. Version and a URI can be useful for understanding what code is being run.

**pipeline-def.json**

```javascript
{
    "name": "My First Pipeline",
    "uri": "https://github.com/wtsi-npg/my-special-pipeline",
    "version": "1.0"
}
```

`url='https://$SERVER:$PORT/pipelines'; curl -L -XPOST ${url} -H "content-type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" -w " %{http_code}" -d @pipeline-def.json`

Keep this pipeline definition with your data, as you will need it to tell npg_porch which pipeline you are acting on.

As with any HTTP server, when communicating with npg_porch you must inspect the response code and message after each communication. See `-w " %{http_code}" above. The API documentation lists the response codes you can expect to have to handle. In this case, the server may respond with 400 - BAD REQUEST if you leave out a name, or 409 - CONFLICT if you chose a name that is already created.

### Step 2 - decide on the unique criteria for running the pipeline

e.g. Once per 24 hours, poll iRODS metadata for data relating to a study.

We might create a cronjob that runs a script. It invokes `imeta` and retrieves a list of results. Now we turn each of those results into a JSON document to our own specification:

*Schema: npg_porch.model.task*

**study-100-id-run-45925.json**

```javascript
{
    "pipeline": {
        "name": "My First Pipeline",
        "uri": "https://github.com/wtsi-npg/my-special-pipeline",
        "version": "1.0"
    },
    "task_input": {
        "study_id": 100,
        "id_run": 45925
    }
}
```

This document will form the basis for npg_porch to decide whether work is new or already seen.

Like any dictionary or Perl hash, order does not matter. The previous document is effectively identical to the following:

```javascript
{
    "task_input": {
        "id_run": 45925,
        "study_id": 100
    },
    "pipeline": {
        "name": "My First Pipeline",
        "uri": "https://github.com/wtsi-npg/my-special-pipeline",
        "version": "1.0"
    }
}
```

However, any change in the number or name of keys as well as the values is different, such as:

```javascript
{
    "task_input": {
        "id_run": 45925,
        "study_id": 100,
        "type": "CRAM"
    },
    ...
}
```

Try to limit the content to the variable parts of pipeline configuration. Settings like `type="CRAM"` might be better as static arguments to the pipeline, rather than part of the definition here.

Note that it is possible to run the same `task_input` with a different `pipeline`. For example, if a task failed, you might release a pipeline update. In order to run the same task again, you would need to register another pipeline and register the same task definition with the new pipeline. We do not currently support updating a pipeline with a new version.

### Step 3 - register the documents with npg_porch

*Schema: npg_porch.model.task*

Now you want the pipeline to run once per specification, and so register the documents with npg_porch.

```bash
url='https://$SERVER:$PORT/tasks'
for DOC in *.json; do
    response=$(curl -w '%{http_code}' -L -XPOST ${url} -H "content-type: application/json" -H "Authorization: Bearer $TOKEN" -d @${DOC}`)

    # parsing the response is left as an exercise for the reader...
    if [[ "$response_code" ne 201]]; then
        echo "Something went wrong! $($response)"
    fi
done
```

We have fewer issues to work around if we access the service via programming language e.g.

```perl
use HTTP::Request;
use LWP::UserAgent;

my $ua = LWP::UserAgent->new;
my $request = HTTP::Request->new(POST => 'https://$SERVER:$PORT/tasks');
$request->content_type('application/json');
$request->header(Accept => 'application/json');
$request->content($DOC);

my $response = $ua->request($request);
if ($response->is_success) {
    print "Submitted successfully\n";
} else {
    die q(It's all gone wrong!)
}
```

**Example 201 server response**

```javascript
{
    "task_input": {
        "id_run": 45925,
        "study_id": 100
    },
    "task_input_id": "a1e556f26db6a950462aebb41251",
    "status": "PENDING"
    "pipeline": {
        "name": "My First Pipeline",
        "uri": "https://github.com/wtsi-npg/my-special-pipeline",
        "version": "1.0"
    }
}
```

Once a task has been submitted, and a 201 CREATED response has been received, the npg_porch server assigns a timestamp to the task, gives it a status of `PENDING` and assigns a unique ID to it. The response from the server contains this extra information.

A 200 OK response means that this particular task for this pipeline has already been registered. The current representation of the task is returned, the status of the task might be different from `PENDING`.  Note that if there are many tasks to register, some of which were submitted previously, further work is required to make the process efficient - such as to ask the npg_porch server for a list of previously registered tasks for this pipeline.

### Step 4 - write a script or program that can launch the pipeline

Supposing there are new tasks created every 24 hours, we then also need a client that checks every 24 hours for new work it can run on a compute farm.

Using the "claim" interface, you can ask npg_porch to earmark tasks that you intend to run. Others will remain unclaimed until this script or another claims them. Generally speaking, tasks are first-in first-out, so the first task you get if you claim one is the first unclaimed task npg_porch was told about.

```bash
url='https://$SERVER:$PORT/tasks/claim'
response=$(curl -L -I -XPOST ${url} -H "content-type: application/json" -H "Authorization: Bearer $TOKEN" -d @pipeline-def.json)
```

Response body:

```javascript
[
    {
        "pipeline": {
            "name": "My First Pipeline",
            "uri": "https://github.com/wtsi-npg/my-special-pipeline",
            "version": "1.0"
        },
        "task_input": {
            "study_id": 100,
            "id_run": 46520
        },
        "task_input_id": "a45eada4a42b99856783"
        "status": "CLAIMED"
    }
]
```

The response is a list because you have the possibility to claim several tasks at once. Each task is the same as when it was submitted in step 3, but the status has changed. From this you can extract your "task_input" parameters and add them to the pipeline invocation.

```bash
jq -r '.[0] | .task_input.study_id, .task_input.id_run'
```

or

```perl
use JSON qw/decode_json/;

my $ua = LWP::UserAgent->new;
my $request = HTTP::Request->new(POST => 'https://$SERVER:$PORT/tasks/claim');
$request->content_type('application/json');
$request->header(Accept => 'application/json');
$request->header(Authorization => "Bearer $TOKEN")

my $response = $ua->request($request);
if ($response->is_success) {
    my $claims = decode_json($response->content);
    foreach my $claim (@$claims) {
        my $command = sprintf 'run_pipeline --study %s --id_run %s', $claim->{task_input}{study_id}, $claim->{task_input}{id_run};
        print $command . "\n";
    }
}
...
```

### Step 5 - Make the pipeline wrapper register completion

Once the pipeline is complete, you can register this with npg_porch to show that the task is over. In the event of failure you can register it as such, or mark it `DONE` so that it is possible to tell if pipelines finished silently without succeeding.

The allowed task states are:
PENDING -> CLAIMED -> RUNNING -> DONE/FAILED/CANCELLED

A failed task might be rerun by changing this status from FAILED to PENDING, such that the above script can again claim it.

### Step 6 - Deal with pipeline failures

Inevitably a pipeline will fail: Disk full, segfault, missing data, missing dependency etc.

T.B.C.
