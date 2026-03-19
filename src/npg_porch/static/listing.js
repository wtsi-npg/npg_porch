(function() {
  const pageConfig = document.getElementById('listing_page');
  if (!pageConfig) {
    return;
  }

  function parseJsonDataset(element, key, fallback) {
    const value = element.dataset[key];
    if (value === undefined || value === '') {
      return fallback;
    }
    try {
      return JSON.parse(value);
    } catch {
      return fallback;
    }
  }

  const taskStateOptions = parseJsonDataset(pageConfig, 'taskStatesJson', []);
  const endpoint = parseJsonDataset(pageConfig, 'endpointJson', '');
  const rowStatusClasses = [
    'table-success',
    'table-primary',
    'table-warning',
    'table-light',
    'table-danger',
    'table-secondary',
    'table-info'
  ];
  const pendingChanges = new Map();
  const rowErrors = new Map();
  let uiCsrfToken = parseJsonDataset(pageConfig, 'uiCsrfTokenJson', null);
  let uiSessionPipelineName = parseJsonDataset(
    pageConfig, 'uiSessionPipelineNameJson', null
  );
  let applyInFlight = false;

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function renderText(value, type) {
    if (value === null || value === undefined) {
      return '';
    }
    const text = String(value);
    // DataTables writes display values as HTML, so escape browser-facing text
    // here to prevent task data and pipeline names becoming markup.
    return type === 'display' ? escapeHtml(text) : text;
  }

  function renderJson(value, type) {
    if (value === null || value === undefined) {
      return '';
    }
    const text = JSON.stringify(value);
    // Task input is user-controlled JSON and must be escaped before display
    // for the same reason as plain-text columns above.
    return type === 'display' ? escapeHtml(text) : text;
  }

  function stableStringify(value) {
    if (value === null || typeof value !== 'object') {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      return `[${value.map((item) => stableStringify(item)).join(',')}]`;
    }
    const entries = Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`);
    return `{${entries.join(',')}}`;
  }

  function buildTaskKey(task) {
    if (!task || !task.pipeline || !task.task_input) {
      return null;
    }
    return `${task.pipeline.name}::${task.pipeline.version}::${stableStringify(task.task_input)}`;
  }

  function updateApplyButton() {
    const applyButton = document.getElementById('apply_state_changes');
    if (!applyButton) {
      return;
    }
    const count = pendingChanges.size;
    applyButton.disabled = count === 0 || applyInFlight;
    applyButton.textContent = `Apply State Changes (${count})`;
  }

  function updateSessionControls() {
    const sessionStatus = document.getElementById('ui_session_status');
    const signInButton = document.getElementById('sign_in_for_updates');
    const signOutButton = document.getElementById('sign_out_of_updates');
    const active = Boolean(uiCsrfToken);

    if (sessionStatus) {
      sessionStatus.textContent = active
        ? `Update session active for pipeline ${uiSessionPipelineName}.`
        : 'No update session active.';
    }
    if (signInButton) {
      signInButton.textContent = active ? 'Switch Update Session' : 'Sign In for Updates';
    }
    if (signOutButton) {
      signOutButton.disabled = !active;
    }
  }

  function setUpdateResult(message, level) {
    const resultElement = document.getElementById('update_result');
    if (!resultElement) {
      return;
    }
    if (!message) {
      resultElement.className = 'alert d-none py-2 mb-0 mt-3';
      resultElement.textContent = '';
      return;
    }
    resultElement.className = `alert alert-${level} py-2 mb-0 mt-3`;
    resultElement.textContent = message;
  }

  function selectedStatusForRow(row) {
    const key = buildTaskKey(row);
    const pending = key ? pendingChanges.get(key) : null;
    return pending ? pending.status : row.status;
  }

  function renderStatusEditor(data, type, row) {
    if (type !== 'display') {
      return selectedStatusForRow(row);
    }
    const key = buildTaskKey(row);
    const currentStatus = selectedStatusForRow(row);
    const options = taskStateOptions.map((option) => {
      const selected = option === currentStatus ? ' selected' : '';
      return `<option value="${escapeHtml(option)}"${selected}>${escapeHtml(option)}</option>`;
    }).join('');
    const hasError = key && rowErrors.has(key);
    const errorMarkup = hasError
      ? `<div class="small text-danger mt-1">${escapeHtml(rowErrors.get(key))}</div>`
      : '';
    const keyAttribute = key ? ` data-task-key="${escapeHtml(key)}"` : '';

    return (
      `<div class="status-editor${pendingChanges.has(key) ? ' status-dirty' : ''}">` +
      `<select class="form-select form-select-sm task-status-select"${keyAttribute}>${options}</select>` +
      `${errorMarkup}` +
      `</div>`
    );
  }

  const table = new DataTable('#tasks', {
    ajax: {
      url: endpoint,
      dataSrc: function(response) {
        return (response.data || []).map((row) => {
          const taskKey = buildTaskKey(row);
          const pending = taskKey ? pendingChanges.get(taskKey) : null;
          return {
            ...row,
            // Preserve original status from first user edit for stable dirty tracking.
            original_status: pending ? pending.original_status : row.status
          };
        });
      }
    },
    processing: true,
    columns: [
      {
        data: 'pipeline.name',
        render: function(data, type) {
          return renderText(data, type);
        }
      },
      {
        data: 'pipeline.version',
        render: function(data, type) {
          return renderText(data, type);
        }
      },
      {
        data: 'task_input',
        render: function(data, type) {
          return renderJson(data, type);
        }
      },
      {
        data: 'status',
        className: 'status-column',
        width: '11rem',
        render: function(data, type, row) {
          return renderStatusEditor(data, type, row);
        }
      },
      {
        data: 'updated',
        render: function(data, type) {
          return renderText(data, type);
        }
      },
      {
        data: 'created',
        render: function(data, type) {
          return renderText(data, type);
        }
      }
    ],
    order: [[4, 'desc' ]],
    rowCallback: function(row, data) {
      $(row).removeClass(rowStatusClasses.join(' '));
      const status = data.status ? data.status.toLowerCase() : '';
      const statusClassMap = {
        'done': 'table-success',
        'running': 'table-primary',
        'claimed': 'table-warning',
        'pending': 'table-light',
        'failed': 'table-danger',
        'cancelled': 'table-secondary'
      };

      const bootstrapClass = statusClassMap[status];
      if (bootstrapClass) {
        $(row).addClass(bootstrapClass);
      }
      const taskKey = buildTaskKey(data);
      if (taskKey && pendingChanges.has(taskKey)) {
        $(row).addClass('table-info');
      }
    }
  });

  $('#tasks tbody').on('change', '.task-status-select', function() {
    const row = $(this).closest('tr');
    const rowData = table.row(row).data();
    if (!rowData) {
      return;
    }
    const taskKey = buildTaskKey(rowData);
    if (!taskKey) {
      return;
    }

    rowErrors.delete(taskKey);
    const selectedStatus = this.value;
    const existingChange = pendingChanges.get(taskKey);
    const originalStatus = existingChange
      ? existingChange.original_status
      : rowData.original_status;
    if (selectedStatus === originalStatus) {
      pendingChanges.delete(taskKey);
    } else {
      pendingChanges.set(taskKey, {
        pipeline: rowData.pipeline,
        task_input: rowData.task_input,
        status: selectedStatus,
        original_status: originalStatus
      });
    }
    updateApplyButton();
    table.draw(false);
  });

  const filterMode = document.getElementById('filter_mode');
  const selectionForm = document.getElementById('selection_form');
  const pipelineSelection = document.getElementById('pipeline_selection');
  const stateSelection = document.getElementById('state_selection');
  const tokenDialog = document.getElementById('token_dialog');
  const tokenInput = document.getElementById('update_token_input');
  const signInButton = document.getElementById('sign_in_for_updates');
  const signOutButton = document.getElementById('sign_out_of_updates');
  const cancelTokenDialogButton = document.getElementById('cancel_token_dialog');
  const tokenForm = document.getElementById('token_form');
  const applyStateChangesButton = document.getElementById('apply_state_changes');
  const tokenFallback = document.getElementById('token_fallback');
  const tokenFallbackForm = document.getElementById('token_fallback_form');
  const tokenFallbackInput = document.getElementById('token_fallback_input');
  const tokenFallbackCancel = document.getElementById('token_fallback_cancel');
  let tokenFallbackResolver = null;

  if (tokenForm) {
    tokenForm.addEventListener('submit', function(event) {
      event.preventDefault();
      if (!tokenInput) {
        tokenDialog.close('cancel');
        return;
      }
      const token = tokenInput.value.trim();
      if (!token) {
        tokenInput.setCustomValidity('Token is required.');
        tokenInput.reportValidity();
        return;
      }
      tokenInput.setCustomValidity('');
      tokenDialog.dataset.submittedToken = token;
      tokenDialog.close('submit');
    });
  }

  if (cancelTokenDialogButton) {
    cancelTokenDialogButton.addEventListener('click', function() {
      if (tokenDialog) {
        tokenDialog.close('cancel');
      }
    });
  }

  function closeTokenFallback(token) {
    if (tokenFallback) {
      tokenFallback.classList.add('d-none');
    }
    const resolver = tokenFallbackResolver;
    tokenFallbackResolver = null;
    if (resolver) {
      resolver(token);
    }
  }

  function showTokenFallback() {
    if (!tokenFallback || !tokenFallbackInput) {
      setUpdateResult(
        'Unable to prompt for token on this browser. Please use a browser with dialog support.',
        'danger'
      );
      return Promise.resolve(null);
    }
    if (tokenFallbackResolver) {
      tokenFallbackResolver(null);
      tokenFallbackResolver = null;
    }
    tokenFallbackInput.value = '';
    tokenFallbackInput.setCustomValidity('');
    tokenFallback.classList.remove('d-none');
    tokenFallbackInput.focus();
    return new Promise((resolve) => {
      tokenFallbackResolver = resolve;
    });
  }

  if (tokenFallbackForm) {
    tokenFallbackForm.addEventListener('submit', function(event) {
      event.preventDefault();
      if (!tokenFallbackInput) {
        closeTokenFallback(null);
        return;
      }
      const token = tokenFallbackInput.value.trim();
      if (!token) {
        tokenFallbackInput.setCustomValidity('Token is required.');
        tokenFallbackInput.reportValidity();
        return;
      }
      tokenFallbackInput.setCustomValidity('');
      tokenFallbackInput.value = '';
      closeTokenFallback(token);
    });
  }

  if (tokenFallbackCancel) {
    tokenFallbackCancel.addEventListener('click', function() {
      closeTokenFallback(null);
    });
  }

  function showTokenDialog() {
    if (!tokenDialog || typeof tokenDialog.showModal !== 'function') {
      return showTokenFallback();
    }
    if (tokenInput) {
      tokenInput.value = '';
      tokenInput.setCustomValidity('');
    }
    delete tokenDialog.dataset.submittedToken;
    tokenDialog.showModal();
    return new Promise((resolve) => {
      const onClose = () => {
        tokenDialog.removeEventListener('close', onClose);
        const submittedToken = tokenDialog.dataset.submittedToken || null;
        delete tokenDialog.dataset.submittedToken;
        resolve(tokenDialog.returnValue === 'submit' ? submittedToken : null);
      };
      tokenDialog.addEventListener('close', onClose);
    });
  }

  async function signInWithToken(token) {
    try {
      const response = await fetch('/ui/session', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify({ token })
      });
      if (!response.ok) {
        setUpdateResult(await parseError(response), 'danger');
        return false;
      }
      const payload = await response.json();
      uiCsrfToken = payload.csrf_token;
      uiSessionPipelineName = payload.pipeline_name;
      updateSessionControls();
      setUpdateResult('Update session created.', 'info');
      return true;
    } catch {
      setUpdateResult('Network error while creating update session.', 'danger');
      return false;
    }
  }

  async function requestUiSession() {
    if (uiCsrfToken) {
      return true;
    }
    const token = await showTokenDialog();
    if (!token) {
      setUpdateResult('Task updates cancelled: no token provided.', 'warning');
      return false;
    }
    return signInWithToken(token);
  }

  if (signInButton) {
    signInButton.addEventListener('click', async function() {
      const token = await showTokenDialog();
      if (token) {
        await signInWithToken(token);
      }
    });
  }

  if (signOutButton) {
    signOutButton.addEventListener('click', async function() {
      if (!uiCsrfToken) {
        return;
      }
      try {
        const response = await fetch('/ui/session', {
          method: 'DELETE',
          headers: {
            'X-CSRF-Token': uiCsrfToken
          },
          credentials: 'same-origin'
        });
        if (!response.ok) {
          setUpdateResult(await parseError(response), 'danger');
          return;
        }
        uiCsrfToken = null;
        uiSessionPipelineName = null;
        updateSessionControls();
        setUpdateResult('Update session cleared.', 'info');
      } catch {
        setUpdateResult('Network error while clearing update session.', 'danger');
      }
    });
  }

  async function parseError(response) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    if (payload && payload.detail) {
      return payload.detail;
    }
    return `Request failed with status ${response.status}`;
  }

  async function applyPendingChanges() {
    if (pendingChanges.size === 0) {
      setUpdateResult('No changes to apply.', 'warning');
      return;
    }
    const sessionReady = await requestUiSession();
    if (!sessionReady || !uiCsrfToken) {
      return;
    }

    applyInFlight = true;
    setUpdateResult('', 'info');
    updateApplyButton();
    rowErrors.clear();

    const updates = Array.from(pendingChanges.entries());
    const responses = await Promise.all(
      updates.map(async ([taskKey, payload]) => {
        try {
          const response = await fetch('/ui/tasks', {
            method: 'PUT',
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'X-CSRF-Token': uiCsrfToken
            },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
          });
          if (response.ok) {
            return { taskKey, ok: true };
          }
          return { taskKey, ok: false, error: await parseError(response) };
        } catch {
          return { taskKey, ok: false, error: 'Network error while updating task' };
        }
      })
    );

    let updated = 0;
    let failed = 0;
    for (const result of responses) {
      if (result.ok) {
        pendingChanges.delete(result.taskKey);
        rowErrors.delete(result.taskKey);
        updated += 1;
      } else {
        rowErrors.set(result.taskKey, result.error);
        failed += 1;
      }
    }

    applyInFlight = false;
    updateApplyButton();
    table.ajax.reload(null, false);
    setUpdateResult(
      `${updated} updated, ${failed} failed.`,
      failed === 0 ? 'success' : 'warning'
    );
  }

  if (applyStateChangesButton) {
    applyStateChangesButton.addEventListener('click', applyPendingChanges);
  }

  function resetStateSelection() {
    if (!stateSelection) {
      return;
    }
    const allOption = Array.from(stateSelection.options).find(
      (option) => option.value === 'All'
    );
    if (allOption) {
      stateSelection.value = allOption.value;
      return;
    }
    const emptyOption = Array.from(stateSelection.options).find(
      (option) => option.value === ''
    );
    if (emptyOption) {
      stateSelection.value = '';
      return;
    }
    stateSelection.selectedIndex = 0;
  }

  function syncFilterMode() {
    if (!filterMode || !pipelineSelection || !stateSelection) {
      return;
    }
    const isAll = filterMode.value === 'all';
    pipelineSelection.disabled = !isAll;
    stateSelection.disabled = !isAll;
    if (!isAll) {
      pipelineSelection.value = '';
      resetStateSelection();
    }
    if (selectionForm) {
      if (filterMode.value === 'long_running') {
        selectionForm.action = '/long_running';
      } else if (filterMode.value === 'recently_failed') {
        selectionForm.action = '/recently_failed';
      } else {
        selectionForm.action = '/';
      }
    }
  }

  if (filterMode) {
    filterMode.addEventListener('change', syncFilterMode);
    syncFilterMode();
  }
  updateSessionControls();
  updateApplyButton();
})();
