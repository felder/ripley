<template>
  <div class="pb-5 px-5">
    <Header1 class="mb-2" text="Create a Course Site" />
    <v-alert
      v-if="error || warning"
      id="canvas-error-container"
      class="mb-3"
      density="compact"
      role="alert"
      type="warning"
    >
      {{ error || warning }}
    </v-alert>
    <div v-if="!isLoading && !error">
      <div v-if="isAdmin && currentWorkflowStep !== 'processing'" class="pl-3">
        <CreateCourseSiteHeader
          :admin-mode="adminMode"
          :admin-terms="adminTerms"
          :current-admin-term="currentAdminTerm"
          :fetch-feed="fetchFeed"
          :is-fetching="isFetching"
          :set-admin-acting-as="setAdminActingAs"
          :set-admin-by-section-ids="setAdminBySectionIds"
          :set-admin-mode="setAdminMode"
          :set-warning="w => warning = w"
          :switch-admin-term="switchAdminTerm"
        />
      </div>
      <div v-if="!isFetching" :class="{'pt-2': isAdmin && currentWorkflowStep !== 'processing'}">
        <div v-if="currentWorkflowStep === 'selecting' && size(teachingTerms)">
          <v-card class="mt-2" elevation="0">
            <v-tabs
              v-if="size(teachingTerms) > 1"
              v-model="selectedTerm"
              aria-label="Official Sections"
              class="tabs-border"
              color="primary"
              slider-color="grey-darken-3"
            >
              <v-tab
                v-for="(term, index) in teachingTerms"
                :id="`term${index}`"
                :key="index"
                aria-controls="official-sections-tabpanel"
                :aria-selected="term.slug === selectedTerm"
                :class="{'rounded-ts-lg': index === 0, 'rounded-te-lg': index === 1}"
                :tabindex="term.slug === selectedTerm ? 0 : -1"
                :value="term.slug"
                variant="elevated"
                width="50%"
              >
                <span
                  class="font-size-16"
                  :class="{'text-white': term.slug === selectedTerm, 'text-primary': term.slug !== selectedTerm}"
                >
                  {{ term.name }}
                </span>
              </v-tab>
            </v-tabs>
            <div class="border pb-5 px-5 pt-3">
              <v-window
                id="official-sections-tabpanel"
                v-model="selectedTerm"
                :aria-labelledby="size(teachingTerms) > 1 ? `term${findIndex(teachingTerms, t => t.slug === selectedTerm)}` : undefined"
                :role="size(teachingTerms) > 1 ? 'tabpanel' : undefined"
              >
                <v-window-item :value="selectedTerm">
                  <h2 id="official-sections-heading">
                    {{ selectedTermName }}
                    {{ actingAsInstructor ? `sections taught by ${actingAsInstructor.name}` : 'Official Sections' }}
                  </h2>
                  <div v-if="size(coursesList)">
                    <div class="text-subtitle-1 mt-1 mb-3">
                      All official sections you select below will be put in ONE, single course site.
                    </div>
                    <SelectSectionsGuide />
                    <v-expansion-panels
                      v-model="panels"
                      class="my-5"
                      multiple
                    >
                      <v-expansion-panel
                        v-for="course in coursesList"
                        :id="`sections-course-${course.slug}`"
                        :key="course.course_id"
                        :value="course.slug"
                        bg-color="blue-lighten-5"
                      >
                        <v-expansion-panel-title :id="`sections-course-${course.slug}-btn`">
                          <template #actions="{ expanded }">
                            <v-icon :icon="expanded ? mdiMenuDown : mdiMenuRight" />
                          </template>
                          <h3 :id="`sections-course-title-${course.slug}`" class="sections-course-title">
                            <CourseCodeAndTitle :course="course" />
                          </h3>
                        </v-expansion-panel-title>
                        <v-expansion-panel-text>
                          <CourseSectionsTable
                            :id="`template-sections-table-${course.slug}`"
                            :key="course.slug"
                            class="mb-1 mt-4"
                            mode="createCourseForm"
                            :sections="course.sections"
                            :table-caption="courseSectionsTableCaption(course)"
                            table-clazz="border-0"
                            :update-selected="updateSelected"
                          />
                        </v-expansion-panel-text>
                      </v-expansion-panel>
                    </v-expansion-panels>
                  </div>
                  <div v-if="!size(coursesList)" class="text-subtitle-1 mt-1 mb-3">
                    No matching course sections found.
                  </div>
                </v-window-item>
              </v-window>
              <div class="d-flex justify-end mt-2">
                <v-btn
                  id="page-create-course-site-continue"
                  aria-label="Continue to next step"
                  class="mr-1"
                  color="primary"
                  :disabled="!selectedSectionsList.length"
                  @click="showConfirmation"
                >
                  Next
                </v-btn>
                <v-btn
                  id="page-create-course-site-cancel"
                  aria-label="Cancel and return to Site Creation Overview"
                  variant="tonal"
                  @click="cancel"
                >
                  Cancel
                </v-btn>
              </div>
            </div>
          </v-card>
        </div>
        <div v-if="currentWorkflowStep === 'confirmation'">
          <ConfirmationStep
            :course-site-creation-promise="courseSiteCreationPromise"
            :current-semester-name="currentSemesterName"
            :go-back="onCancelConfirmationStep"
            :selected-sections-list="selectedSectionsList"
          />
        </div>
        <div
          v-if="currentWorkflowStep === 'processing'"
          aria-live="polite"
          role="alert"
        >
          <div class="pl-8 pr-16 py-4">
            <div class="pb-3">
              <span v-if="jobStatus === 'sendingRequest'">Sending request...</span>
              <span v-if="jobStatus === 'queued'">Request sent. Awaiting processing...</span>
              <span v-if="jobStatus === 'started'">Request received. Provisioning course site...</span>
              <span v-if="jobStatus === 'finished'">Finishing up...</span>
            </div>
            <v-progress-linear
              color="primary"
              height="10"
              indeterminate
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import ConfirmationStep from '@/components/bcourses/create/ConfirmationStep'
import CourseCodeAndTitle from '@/components/bcourses/create/CourseCodeAndTitle'
import CourseSectionsTable from '@/components/bcourses/CourseSectionsTable'
import CreateCourseSiteHeader from '@/components/bcourses/create/CreateCourseSiteHeader'
import Header1 from '@/components/utils/Header1'
import SelectSectionsGuide from '@/components/bcourses/create/SelectSectionsGuide'
import {findIndex} from 'lodash'
import {mdiMenuDown, mdiMenuRight} from '@mdi/js'
</script>

<script>
import Context from '@/mixins/Context'
import {courseCreate, courseProvisionJobStatus, getCourseProvisioningMetadata, getSections} from '@/api/canvas-site'
import {each, find, get, includes, map, size} from 'lodash'
import {iframeParentLocation, putFocusNextTick} from '@/utils'

export default {
  name: 'CreateCourseSite',
  mixins: [Context],
  data: () => ({
    actingAsInstructor: undefined,
    adminActingAs: undefined,
    adminBySectionIds: undefined,
    adminMode: 'actAs',
    adminTerms: [],
    backgroundJobId: undefined,
    canvasSite: undefined,
    canvasSiteId: undefined,
    coursesList: [],
    currentAdminTerm: undefined,
    currentSemester: undefined,
    currentSemesterName: undefined,
    currentWorkflowStep: undefined,
    error: undefined,
    errorConfig: {
      header: undefined,
      supportAction: undefined,
      supportInfo: undefined
    },
    isFetching: false,
    isTeacher: undefined,
    isUidInputMode: true,
    jobStatus: undefined,
    linkToSiteOverview: undefined,
    panels: [],
    percentComplete: undefined,
    selectedSectionsList: undefined,
    selectedTerm: undefined,
    semester: undefined,
    teachingTerms: [],
    timeoutPromise: undefined,
    warning: undefined
  }),
  computed: {
    isAdmin() {
      return this.currentUser.isAdmin || this.currentUser.isCanvasAdmin
    },
    selectedTermName() {
      const term = find(this.teachingTerms, t => t.slug === this.selectedTerm)
      return get(term, 'name', '')
    }
  },
  watch: {
    selectedTerm(slug) {
      if (slug) {
        this.updateSemesterData(slug)
      }
    }
  },
  created() {
    getCourseProvisioningMetadata().then(data => {
      this.updateMetadata(data)
      if (!this.teachingTerms.length && !this.isAdmin) {
        this.warning = 'You are not listed as an instructor of any courses in the current or upcoming term.'
      }
      if (size(this.selectedSectionsList)) {
        this.panels = Array.from({length: this.coursesList.length}, (value, index) => index)
      } else if (this.coursesList.length === 1) {
        this.panels = [0]
      }
      this.actingAsInstructor = this.getActingAsInstructor()

      this.$ready()
    }, error => {
      this.error = error
      this.$ready()
    })
  },
  methods: {
    cancel() {
      this.$router.push({path: '/manage_sites'})
    },
    classCount(semesters) {
      let count = 0
      if (size(semesters) > 0) {
        each(semesters, semester => {
          count += semester.classes.length
        })
      }
      return count
    },
    courseSectionsTableCaption(course) {
      let caption = 'Official sections in this course. Use the checkboxes in the Action column to select sections'
      if (size(course.sections) > 1) {
        caption += ', or use the "Select All" button above.'
      }
      return caption
    },
    courseSiteCreationPromise(siteName, siteAbbreviation) {
      return new Promise((resolve, reject) => {
        const onError = message => {
          this.percentComplete = 0
          this.currentWorkflowStep = null
          this.jobStatus = 'error'
          this.warning = message
          putFocusNextTick('page-title')
          reject()
        }
        this.currentWorkflowStep = 'processing'
        this.jobStatus = 'sendingRequest'
        this.updateSelected()
        const sectionIds = map(this.selectedSectionsList, 'id')
        if (sectionIds.length > 0) {
          const adminActingAs = this.isAdmin && this.adminMode === 'actAs' ? this.adminActingAs : null
          const adminBySectionIds = this.isAdmin && this.adminMode === 'bySectionId' ? this.adminBySectionIds : null
          const adminTermSlug = this.isAdmin && this.adminMode === 'bySectionId' ? this.currentAdminTerm : null
          courseCreate(
            adminActingAs,
            adminBySectionIds,
            adminTermSlug,
            sectionIds,
            siteAbbreviation,
            siteName,
            this.currentSemester
          ).then(
            data => {
              this.backgroundJobId = data.jobId
              this.jobStatus = data.jobStatus
              this.alertScreenReader('Started course site creation.')
              this.trackBackgroundJob()
              resolve()
            },
            () => onError('Failed to start course provisioning job.')
          )
        } else {
          onError('No section IDs were provided.')
        }
      })
    },
    fetchFeed() {
      this.warning = null
      this.isFetching = true
      this.currentWorkflowStep = 'selecting'
      this.backgroundJobId = undefined
      this.jobStatus = undefined
      this.percentComplete = undefined
      this.selectedSectionsList = []
      this.alertScreenReader('Loading courses and sections')

      const semester = (this.adminMode === 'bySectionId' ? this.currentAdminTerm : this.currentSemester)
      getSections(
        this.adminActingAs,
        this.adminBySectionIds,
        this.adminMode,
        semester,
        this.isAdmin
      ).then(
        data => {
          this.updateMetadata(data)
          this.usersClassCount = this.classCount(data.teachingTerms)
          this.teachingTerms = data.teachingTerms
          if (!this.teachingTerms.length && this.adminMode) {
            this.warning = this.adminActingAs ? `UID ${this.adminActingAs} is not listed as an instructor of any courses in the current or upcoming term.` : 'No matching courses found.'
          }
          this.fillCourseSites(this.teachingTerms)
          this.alertScreenReader('Course sections have loaded')
          if (this.adminMode === 'bySectionId' && this.adminBySectionIds) {
            each(this.coursesList, course => {
              each(course.sections, section => {
                section.selected = includes(this.adminBySectionIds, section.id)
              })
            })
            this.updateSelected()
          }
          if (!this.isAdmin && !this.usersClassCount) {
            this.warning = 'Sorry, you are not an admin user and you have no classes.'
          }
        },
        error => {
          this.alertScreenReader('Course section loading failed')
          this.warning = error || 'failure'
        }
      ).finally(() => {
        this.isFetching = false
        putFocusNextTick(this.adminMode === 'bySectionId' ? 'sections-by-ids-button' : 'sections-by-uid-button')
      })
    },
    fillCourseSites(semestersFeed) {
      each(semestersFeed, semester => {
        each(semester.classes, course => {
          course.allSelected = false
          course.selectToggleText = 'All'
          let hasSites = false
          let sectionIdToSites = {}
          if (hasSites) {
            course.hasSites = hasSites
            each(course.sections, section => {
              if (sectionIdToSites[section.id]) {
                section.sites = sectionIdToSites[section.id]
              }
            })
          }
        })
      })
    },
    getActingAsInstructor() {
      let instructor
      if (this.adminActingAs) {
        each(this.teachingTerms, t => each(t.classes, c => each(c.sections, s => each(s.instructors, i => {
          if (i.uid === this.adminActingAs) {
            instructor = i
            return false
          }
        }))))
      }
      return instructor
    },
    onCancelConfirmationStep() {
      this.currentWorkflowStep = 'selecting'
    },
    setAdminActingAs(uid) {
      this.adminActingAs = uid
      this.adminBySectionIds = null
    },
    setAdminBySectionIds(sectionIds) {
      this.adminBySectionIds = sectionIds
      this.adminActingAs = null
    },
    setAdminMode(adminMode) {
      this.adminMode = adminMode
      this.currentWorkflowStep = undefined
      this.coursesList = []
    },
    setTermSlug(slug) {
      if (this.selectedTerm === slug) {
        this.updateSemesterData(this.selectedTerm)
      } else {
        // If the selectedTerm value is changing, updateSemesterData will be called by the 'watch' property set above
        this.selectedTerm = slug
      }
    },
    showConfirmation() {
      this.updateSelected()
      this.alertScreenReader('Course site details form loaded.')
      this.currentWorkflowStep = 'confirmation'
    },
    size,
    switchAdminTerm(semester) {
      if (semester && this.currentAdminTerm !== semester.slug) {
        this.currentWorkflowStep = null
        this.currentAdminTerm = semester.slug
        this.selectedSectionsList = []
        this.updateSelected()
      }
    },
    trackBackgroundJob() {
      this.exportTimer = setInterval(() => {
        courseProvisionJobStatus(this.backgroundJobId).then(
          response => {
            if (response.jobStatus !== this.jobStatus) {
              this.jobStatus = response.jobStatus
            } else {
              this.alertScreenReader(`Still ${includes(['sendingRequest', 'queued'], this.jobStatus) ? 'waiting' : 'processing'}`)
            }
            if (!(includes(['started', 'queued'], this.jobStatus)) || get(response, 'jobData.courseSiteUrl')) {
              clearInterval(this.exportTimer)
              if (get(response, 'jobData.courseSiteUrl')) {
                this.alertScreenReader('Done. Loading new course site.')
                if (this.$isInIframe) {
                  iframeParentLocation(response.jobData.courseSiteUrl)
                } else {
                  window.location.href = response.jobData.courseSiteUrl
                }
              } else {
                this.alertScreenReader('Error.', 'assertive')
                this.currentWorkflowStep = null
                this.jobStatus = 'error'
                this.warning = 'An error has occurred with your request. Please try again or contact bCourses support.'
                putFocusNextTick('page-title')
              }
            }
          }
        ).catch(
          () => {
            this.alertScreenReader('Error.', 'assertive')
            this.currentWorkflowStep = null
            this.jobStatus = 'error'
            this.warning = 'An error has occurred with your request. Please try again or contact bCourses support.'
            clearInterval(this.exportTimer)
            putFocusNextTick('page-title')
          }
        )
      }, 4000)
    },
    updateMetadata(data) {
      this.teachingTerms = data.teachingTerms
      if (size(this.teachingTerms) > 0) {
        this.setTermSlug(this.teachingTerms[0].slug)
      }
      this.fillCourseSites(this.teachingTerms)
      if (this.isAdmin) {
        this.adminActingAs = data.adminActingAs
        this.adminTerms = data.adminTerms
        if (size(this.teachingTerms) > 0 && this.adminTerms.length) {
          this.setTermSlug(this.teachingTerms[0].slug)
        }
        if (size(this.adminTerms) > 0 && !this.currentAdminTerm) {
          this.switchAdminTerm(this.adminTerms[0])
        }
      } else {
        this.currentWorkflowStep = 'selecting'
      }
    },
    updateSelected() {
      this.selectedSectionsList = []
      each(this.coursesList, course => {
        each(course.sections, section => {
          if (section.selected) {
            section.courseTitle = course.title
            this.selectedSectionsList.push(section)
          }
        })
      })
    },
    updateSemesterData(slug) {
      const teachingTerm = find(this.teachingTerms, t => t.slug === slug)
      const term = teachingTerm || find(this.adminTerms, t => t.slug === slug)
      this.coursesList = teachingTerm ? teachingTerm.classes : []
      this.currentSemester = slug
      this.currentSemesterName = term.name
      this.selectedSectionsList = []
      this.alertScreenReader(`Course sections for ${term.name} loaded`)
      this.updateSelected()
    }
  }
}
</script>

<!-- eslint-disable-next-line vue-scoped-css/enforce-style-type -->
<style>
.v-expansion-panel-text__wrapper {
  padding: 8px 12px 16px !important;
}
</style>

<style scoped lang="scss">
.sections-course-title {
  font-size: 15px !important;
  font-weight: 700 !important;
  line-height: 15px;
}
.tabs-border {
  -moz-border-radius: 0;
  -webkit-border-radius: 8px 8px 0 0;
  border: 1px solid $color-container-grey-border;
  border-radius: 8px 8px 0 0;
}
</style>
