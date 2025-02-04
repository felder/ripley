<template>
  <div v-if="!isLoading" class="px-5 pb-5">
    <div>
      <Header1 text="Create Mailing List" />
      <v-alert
        v-if="!error && !success"
        class="mb-3"
        :closable="true"
        density="compact"
        text="No Mailing List has been created for this site."
        type="info"
      />
      <div id="mailing-lists-alert" aria-live="polite" role="alert">
        <v-alert
          v-if="success"
          :closable="true"
          density="compact"
          :text="success"
          type="success"
        />
        <v-alert
          v-if="error"
          density="compact"
          :text="error"
          type="warning"
        />
      </div>
    </div>
    <v-card
      v-if="!error"
      id="mailing-list-details"
      class="ma-0 pa-4"
      elevation="2"
    >
      <v-card-text>
        <div v-if="!isAdminToolMode" class="mb-1">
          bCourses Mailing Lists allow Teachers, TAs, Lead TAs and Readers to send email to everyone in a bCourses site
          by giving the site its own email address. Messages sent to this address from the
          <span class="font-weight-bold">official berkeley.edu email address</span> of a Teacher, TA, Lead TA or Reader
          will be sent to the official email addresses of all site members. Students and people not in the site cannot
          send messages through Mailing Lists.
        </div>
        <div>
          <v-container class="pa-0" fluid>
            <v-row v-if="isAdminToolMode" no-gutters>
              <v-col cols="auto" class="me-auto">
                <h2 v-if="get(canvasSite, 'url')">
                  <OutboundLink
                    id="course-site-href"
                    class="align-start d-flex font-size-18"
                    :href="canvasSite.url"
                    title="View course site"
                  >
                    {{ canvasSite.name }}
                  </OutboundLink>
                </h2>
                <div v-if="!get(canvasSite, 'url')">
                  <h2>{{ canvasSite.name }}</h2>
                </div>
              </v-col>
            </v-row>
            <v-row v-if="isAdminToolMode" no-gutters>
              <v-col>
                <div class="mb-4 w-auto">
                  <div v-if="get(canvasSite, 'term')" class="text-subtitle-1">{{ canvasSite.term.name }}</div>
                  <div>bCourses Site ID {{ get(canvasSite, 'canvasSiteId') }}</div>
                </div>
              </v-col>
            </v-row>
            <v-row align="center" no-gutters>
              <v-col>
                <label class="sr-only" for="mailing-list-name-input">Mailing list name</label>
                <v-text-field
                  id="mailing-list-name-input"
                  v-model="mailingListName"
                  :aria-invalid="hasInvalidCharacters"
                  aria-required="true"
                  density="comfortable"
                  :disabled="isCreating"
                  hide-details
                  maxlength="50"
                  required
                  variant="outlined"
                  @focus="hasInvalidCharacters = false; debouncedValidateName()"
                  @update:model-value="hasInvalidCharacters = false; debouncedValidateName()"
                  @keydown.enter="create"
                />
                <div v-if="mailingListName && hasInvalidCharacters" aria-live="assertive" class="validation-messages">
                  <div class="pr-1 text-no-wrap">
                    <span class="sr-only">Error: </span>Only lowercase alphanumeric, underscore and hyphen characters allowed.
                  </div>
                </div>
              </v-col>
              <v-col>
                <div class="text-no-wrap text-subtitle-1">-{{ mailingListSuffix }}@{{ mailgunDomain }}</div>
              </v-col>
            </v-row>
            <v-row no-gutters>
              <v-col>
                <div class="d-flex float-right mt-8">
                  <div :class="{'mr-2': isAdminToolMode}">
                    <v-btn
                      id="btn-create-mailing-list"
                      color="primary"
                      :disabled="isCreating || !trim(mailingListName) || hasInvalidCharacters"
                      @click="create"
                    >
                      <span v-if="!isCreating">Create mailing list</span>
                      <span v-if="isCreating">
                        <SpinnerWithinButton /> Creating...
                      </span>
                    </v-btn>
                  </div>
                  <div v-if="isAdminToolMode">
                    <v-btn
                      id="btn-cancel"
                      :disabled="isCreating"
                      variant="tonal"
                      @click="cancel"
                    >
                      Cancel
                    </v-btn>
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-container>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
import Context from '@/mixins/Context'
import Header1 from '@/components/utils/Header1.vue'
import MailingList from '@/mixins/MailingList.vue'
import OutboundLink from '@/components/utils/OutboundLink'
import SpinnerWithinButton from '@/components/utils/SpinnerWithinButton.vue'
import {createMailingList, getMailingList, getSuggestedMailingListName} from '@/api/mailing-list'
import {debounce, get, size, trim} from 'lodash'
import {getCanvasSite} from '@/api/canvas-site'
import {nextTick} from 'vue'
import {toInt} from '@/utils'

export default {
  name: 'MailingListCreate',
  components: {Header1, OutboundLink, SpinnerWithinButton},
  mixins: [Context, MailingList],
  data: () => ({
    canvasSiteId: undefined,
    debouncedValidateName: undefined,
    error: undefined,
    hasInvalidCharacters: false,
    isAdminToolMode: undefined,
    isCreating: false,
    mailgunDomain: undefined,
    mailingListName: undefined,
    mailingListSuffix: undefined,
    success: undefined,
    validNameRegex: /[a-z0-9_-]/g
  }),
  created() {
    this.debouncedValidateName = debounce(this.validateName, 200)
  },
  mounted() {
    this.init()
    const canvasSiteIdFromRoute = toInt(get(this.$route, 'params.canvasSiteId'))
    this.isAdminToolMode = !!canvasSiteIdFromRoute
    this.canvasSiteId = canvasSiteIdFromRoute || this.currentUser.canvasSiteId
    getMailingList(this.canvasSiteId).then(
      data => {
        this.setMailingList(data)
        if (data) {
          this.goToNextPage()
        } else {
          this.getCanvasSite().then(data => {
            this.setCanvasSite(data)
            getSuggestedMailingListName(this.canvasSiteId).then(data => {
              this.mailgunDomain = data.mailgunDomain
              this.mailingListName = data.name
              const suffix = data.suffix
              this.mailingListSuffix = suffix
              this.$ready()
            })
          })
        }
      },
      error => {
        this.error = error
        this.$ready()
      }
    )
  },
  methods: {
    cancel() {
      this.alertScreenReader('Canceled. Nothing saved.', 'assertive')
      nextTick(this.$router.push({path: '/mailing_list/select_course'}))
    },
    create() {
      const name = trim(this.mailingListName)
      if (name && !this.hasInvalidCharacters) {
        this.isCreating = true
        this.alertScreenReader('Creating mailing list.')
        const createTimer = setInterval(() => {
          this.alertScreenReader('Still creating mailing list.')
        }, 7000)
        createMailingList(
          this.canvasSiteId,
          `${name}-${this.mailingListSuffix}`,
          !this.isAdminToolMode
        ).then(
          data => {
            this.alertScreenReader('Success.', 'assertive')
            this.error = null
            this.setMailingList(data)
            nextTick(this.goToNextPage())
          },
          error => {
            this.alertScreenReader('Error.', 'assertive')
            this.error = error
          }
        ).finally(() => {
          clearInterval(createTimer)
          this.isCreating = false
        })
      }
    },
    get,
    getCanvasSite() {
      return new Promise(resolve => {
        if (this.canvasSite) {
          resolve(this.canvasSite)
        } else {
          getCanvasSite(this.canvasSiteId).then(resolve)
        }
      })
    },
    goToNextPage() {
      const path = this.isAdminToolMode ? '/mailing_list/update' : '/mailing_list/send_welcome_email'
      this.$router.push({path})
    },
    trim,
    validateName() {
      const name = trim(this.mailingListName)
      const isValid = name.length && size(name.match(this.validNameRegex)) === name.length && name[0].match(/[a-z]/)
      this.hasInvalidCharacters = !isValid
    }
  }
}
</script>
