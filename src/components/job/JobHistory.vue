<template>
  <v-card class="elevation-2" color="grey-lighten-4" outlined>
    <v-card-title>
      <div class="align-start d-flex py-3">
        <h2 class="ml-2 mt-3">
          <div class="align-center d-flex">
            <div class="pr-2">
              <v-icon
                :color="$vuetify.theme.dark ? 'white' : 'primary'"
                :icon="mdiHistory"
                size="large"
              />
            </div>
            <h2>Job History</h2>
          </div>
        </h2>
        <v-spacer />
        <v-text-field
          v-if="size(jobHistory)"
          v-model="search"
          :append-inner-icon="mdiMagnify"
          class="bg-white"
          hide-details
          label="Search History"
          single-line
          variant="outlined"
        />
      </div>
    </v-card-title>
    <v-card-text>
      <v-data-table
        :headers="headers"
        item-value="id"
        :items="jobHistory"
        density="compact"
        items-per-page="10"
        :search="search"
        show-expand
      >
        <template #no-data>
          <div id="message-no-job-history" class="pa-4 text-no-wrap title">
            {{ search ? 'No matching jobs' : 'Job history is empty' }}
          </div>
        </template>
        <template #item.jobKey="{item}">
          <div class="font-size-15 py-2 text-grey-darken-2">
            {{ item.jobKey }}
          </div>
        </template>
        <template #item.failed="{item}">
          <div class="py-2">
            <v-icon
              v-if="item.finishedAt"
              :color="item.failed ? 'error' : 'success'"
              :icon="item.failed ? mdiAlert : mdiCheckCircle"
            />
            <div v-if="!item.finishedAt">
              <v-progress-circular
                :indeterminate="true"
                rotate="5"
                size="18"
                width="4"
                color="orange"
              />
            </div>
          </div>
        </template>
        <template #item.startedAt="{item}">
          <div class="py-2">
            {{ $moment(item.startedAt).format(dateFormat) }}
          </div>
        </template>
        <template #item.finishedAt="{item}">
          <div v-if="item.finishedAt" class="py-2">
            {{ $moment(item.finishedAt).format(dateFormat) }}
          </div>
        </template>
        <template #expanded-row="{item}">
          <tr class="bg-secondary">
            <td colspan="5" class="px-4 py-2">
              <div><strong>Job result</strong></div>
              <div>{{ item.result || 'No details.' }}</div>
            </td>
          </tr>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>

<script setup>
import {mdiAlert, mdiCheckCircle, mdiHistory, mdiMagnify} from '@mdi/js'
</script>

<script>
import Context from '@/mixins/Context'
import {size} from 'lodash'

export default {
  name: 'JobHistory',
  mixins: [Context],
  props: {
    jobHistory: {
      required: true,
      type: Array
    },
    refreshing: {
      required: true,
      type: Boolean
    }
  },
  data: () => ({
    dateFormat: 'ddd, MMM Do, h:mm:ss A',
    headers: [
      {title: '', key: 'jobKey', sortable: false},
      {title: 'Status', key: 'failed'},
      {title: 'Started', key: 'startedAt'},
      {title: 'Finished', key: 'finishedAt'}
    ],
    search: undefined
  }),
  methods: {
    size
  }
}
</script>
