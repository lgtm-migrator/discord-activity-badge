"""
Copyright 2021 Janrey "Codexlink" Licas

licensed under the apache license, version 2.0 (the "license");
you may not use this file except in compliance with the license.
you may obtain a copy of the license at

	http://www.apache.org/licenses/license-2.0

unless required by applicable law or agreed to in writing, software
distributed under the license is distributed on an "as is" basis,
without warranties or conditions of any kind, either express or implied.
see the license for the specific language governing permissions and
limitations under the license.
"""

if __name__ == "__main__":
    from elements.exceptions import IsolatedExecNotAllowed

    raise IsolatedExecNotAllowed

import os
from asyncio import create_task, ensure_future, Future, sleep as asyncio_sleep, wait
from re import compile, Match, MULTILINE, Pattern
from typing import Any, Optional, Union
from datetime import datetime, timedelta

from elements.constants import (
    B64_ACTION_FILENAME,
    BADGE_BASE_SUBJECT,
    BADGE_BASE_URL,
    BADGE_ICON,
    BADGE_NO_COLOR_DEFAULT,
    BADGE_REDIRECT_BASE_DOMAIN,
    BADGE_REGEX_STRUCT_IDENTIFIER,
    Base64Actions,
    BADGE_BASE_MARKDOWN,
    ContextOnSubject,
    DISCORD_USER_STRUCT,
    GithubRunnerActions,
    PreferredActivityDisplay,
    PreferredTimeDisplay,
    TIME_STRINGS,
)
from elements.typing import (
    ActivityDictName,
    BadgeElements,
    BadgeStructure,
    Base64Bytes,
    Base64String,
    ColorHEX,
    HttpsURL,
    READMEContent,
    READMERawContent,
    ResolvedClientResponse,
)
from base64 import b64decode, b64encode
from urllib.parse import quote
from logging import Logger


class BadgeConstructor:
    # * The following variables are declared since there's no typing hint inheritance.
    logger: Logger
    envs: Any
    _user_ctx: DISCORD_USER_STRUCT
    """

    An async-class module that generate badge over-time.
    """

    async def _handle_b64(
        self,
        action: Base64Actions,
        ctx_inout: Union[Base64String, READMERawContent],
    ) -> Union[Base64Bytes, Base64String]:  # To be annotated later.

        type_assert: bool = ctx_inout is Base64String(ctx_inout) or ctx_inout is READMERawContent(ctx_inout) # type: ignore. Subject to change.

        # todo: To be revised.
        if action is Base64Actions.DECODE_B64_TO_BUFFER and type_assert:
            self.logger.debug(
                "Convertion from Base64 to README Markdown Format is done!"
            )

            return Base64String(str(b64decode(ctx_inout), encoding="utf-8"))

        elif action is Base64Actions.ENCODE_BUFFER_TO_B64 and type_assert:
            return Base64Bytes(b64encode(bytes(ctx_inout, encoding="utf-8")))

        else:
            self.logger.critical(f"Passed `action` parameter is not a {Base64Actions}! Please contact the developer if this issue occured in Online Runner.")
            exit()


    async def check_and_update_badge(self, readme_ctx: Base64String) -> Base64String:
        self.logger.info("Converting README to Markdown File...")

        _readme_decode: Future = create_task(
            self._handle_b64(Base64Actions.DECODE_B64_TO_BUFFER, readme_ctx),
            name="READMEContents_Decode",
        )

        self._re_pattern: Pattern = compile(BADGE_REGEX_STRUCT_IDENTIFIER)
        self.logger.info("RegEx for Badge Identification in README Compiled.")

        await wait([_readme_decode])
        self.logger.info("Identifying the badge inside README.md...")


        try:
            is_matched: bool = False

            while not is_matched:

                line_ctx: Union[READMERawContent] = _readme_decode.result()

                match: Optional[Match[Any]] = self._re_pattern.search(line_ctx)

                self.logger.debug(
                    f"Match Result: {match}"
                )

                if match:

                    is_matched = True
                    identifier_name: str = match.group("badge_identifier")

                    is_badge_identified: bool = identifier_name == self.envs["BADGE_IDENTIFIER_NAME"]

                    self.logger.info(
                        (
                            f"Badge with Identifier {identifier_name} found! Substituting the old badge."
                        )
                        if self.envs["BADGE_IDENTIFIER_NAME"] == identifier_name
                        else "Badge with Identifier (%s) not found! New badge will append on the top of the contents of README.md. Please arrange/move the badge once changes has been pushed!"
                        % self.envs["BADGE_IDENTIFIER_NAME"]
                    )

                    await wait([self.badge_task])

                    constructed_badge: BadgeStructure = self.badge_task.result()

                    self.logger.debug(
                        f"Badge Output from Badge Construction Function (construct_badge) (for Replacement) | {constructed_badge}"
                    )

                    line_ctx = line_ctx.replace(match.group(0), constructed_badge) if is_badge_identified else f"{constructed_badge}\n\n{line_ctx}"

                    self.logger.debug(f"README Contents with Changes Reflected!")
                    break


                # At this point, we do the substitution here and run the b64_action for encoding then back.

            return await self._handle_b64(Base64Actions.ENCODE_BUFFER_TO_B64, line_ctx)

        except IndexError as Err:
            self.logger.warn(
                f"The RegEx can't find any badge with Identifier in README. If you think that this is a bug then please let the developer know. | Info: {Err}"
                )

    async def _replace_content(self, constructed_badge: BadgeStructure) -> Any:
        if not self._is_badge_identified:
            self.logger.info(
                "Badge is not found, will append on the top of the README.md."
            )

            # with open

    async def construct_badge(
        self,
    ) -> BadgeStructure:  # todo: Do something about how we pass the data to commit it.
        """
        For every possible arguments declared in actions.yml, the output of the badge will change.

        Let the following be the construction recipe for the badge: [![<badge_identifier>](<badge_url>)](redirect_url)

        Where:
                        - badge_identifier: Unique Name of the Badge
                        - badge_url: The badge URL that is rendered in Markdown (README).
                        - redirect_url: The url to redirect when the badge is clicked.

        ! The badge itself should be recognizable by RegEx declared in elements/constants.py:49 (BADGE_REGEX_STRUCT_IDENTIFIER)

        There are two parts that makes up the whole structure:
                        - Subject
                        - Status

                        * These are basically left and right parts of the badge, more of a pill illustration, but I hope you get the point.

        The badge consists of multiple parts, the following is the diminished structure on how we can manipulate it.
                        Subject consists of  [Icon > Text (Either UserState or ActivityState) > Foreground (HEX from UserState or ActivityState)]
                        Badge consists of [User State or DerivedBaseActivity > Detail > Denoter > Time Elapsed or Remaining > Foreground(HEX from UserState or ActivityState)]] (2)

        ! The way how it represents by order does not mean the handling of parameters are by order!
        * Every User State represents Derived Classes from disocord.BaseActivity.

        # Further Examples: is declared under README.md. (Subsection Activity States)

        Conditions for badge_identifier:
                        - Should be similar that is declared under workflows.
                        - () and - _ can be invoked and identified by the Regex.
                        - Whenever we have one in the README: We can just replace that string and use re.sub then commit and push.
                        - If otherwise: we will create a badge and put it on top. Let the user put it somewhere else they like.

        @o: There's no impactful changes even with per condition. Just references.

        Conditions for redirect_url:
                        - The output of this would probably be the repository of the special repository or anything else.

        """

        # These variables shouldn't be de-alloc'd until we finish the whole function, not just from the try-except scope.
        _subject_output: Union[BadgeStructure, BadgeElements] = BadgeStructure("")
        _status_output: Union[BadgeStructure, BadgeElements] = BadgeStructure("")
        _preferred_activity: ActivityDictName = ActivityDictName("")
        _is_preferred_exists: bool = False

        try:
            _redirect_url: HttpsURL = BADGE_REDIRECT_BASE_DOMAIN + (
                self.envs["URL_TO_REDIRECT_ON_CLICK"]
                if self.envs["URL_TO_REDIRECT_ON_CLICK"]
                else "{0}/{0}".format(self.envs["GITHUB_ACTOR"])
            )  # Let's handle this one first before we attempt to do everything thard.

            self.logger.info(
                "Other elements preloaded, waiting for Discord Client to finish before proceeding..."
            )

            await wait([self._discord_client_task])  # Checkpoint.

            self.logger.info(
                "Discord Client is done. Attempting to process other badge elements..."
            )

            _presence_ctx: dict[str, Union[int, str, slice]] = self._user_ctx[
                "activities"
            ]  # * Append any activity if there's one. We assure that this is dict even with len() == 0.

            _contains_activities: bool = bool(len(_presence_ctx))

            if _contains_activities:  # Does _presence_ctx really contains something?

                # If yes, check what activity is it so that we could process other variables by locking into it.
                # This is were we gonna check if preferred activity exist.

                for (
                    each_cls
                ) in (
                    PreferredActivityDisplay
                ):  # We cannot do key to value lookup, iterate through enums instead.
                    if self.envs["PREFERRED_ACTIVITY_TO_DISPLAY"] is each_cls:
                        if (
                            _presence_ctx.get(each_cls.name) is not None
                        ):  # Is activity really exists?
                            _preferred_activity = ActivityDictName(each_cls.name)
                            _is_preferred_exists = True
                            break

                if (  # We need to better handle this one.
                    not _is_preferred_exists
                ):  # If we fail to lookup, perform exporting keys and convert them to list to use the first activity (if there's any).
                    _fallback_activity: list[str] = list(_presence_ctx.keys())

                    # Do _presence_ctx contain more than one? Let's assert that.
                    if not _fallback_activity:
                        self.logger.warn(
                            "There's are no other activities existing, even with the preferred activity! Fallback to Basic Badge Formation."
                        )
                    else:
                        _preferred_activity = ActivityDictName(_fallback_activity[0])

                self.logger.info(
                    f"Preferred Activity %s %s"
                    % (
                        self.envs["PREFERRED_ACTIVITY_TO_DISPLAY"],
                        "exists!"
                        if _is_preferred_exists
                        else f"does not exists. Using other activity such as {_preferred_activity}.",
                    )
                )

            else:
                self.logger.warning(
                    "There's no activities detected by the time it was fetched."
                )

            # Check if we should append User's State instead of Activity State in the Subject.
            _state_string = "%s_STRING" % (
                _preferred_activity
                if len(_preferred_activity)
                else "%s_STATUS" % self._user_ctx["statuses"]["status"].name.upper()
            )
            _subject_output = (
                BADGE_BASE_SUBJECT
                if not _contains_activities
                and self.envs["STATIC_SUBJECT_STRING"] is None
                else (
                    self.envs[  # ! Add Static Subject String. If that is included, disabled this condition.
                        _state_string
                        if self.envs["STATIC_SUBJECT_STRING"] is None
                        else "STATIC_SUBJECT_STRING"
                    ]
                )
            )

            # ! Keep in mind that the way how this was constructed was done under 3 different inlined parts. Hard to read but less of a mess.
            # todo: For every _x_output, we have to know document it step by step.
            # This part is where do we need to embed the state under Subject or Status.

            # There are lot more conditions to consider to this point.
            """
            If there's no presence ctx and there's not
            """
            _seperator: BadgeElements = BadgeElements(
                (
                    ", "
                    if self.envs["STATUS_CONTEXT_SEPERATOR"] is None
                    else " %s " % self.envs["STATUS_CONTEXT_SEPERATOR"]
                )
                if (
                    self.envs["PREFERRED_PRESENCE_CONTEXT"]
                    is not ContextOnSubject.CONTEXT_DISABLED
                    or self.envs["TIME_DISPLAY_OUTPUT"]
                    is not PreferredTimeDisplay.TIME_DISABLED
                )
                and _contains_activities
                else ""
            )

            _status_output = (
                (  # # Appends Activity or User's State if `STATIC_SUBJECT_STRING` is None.
                    "%s " % self.envs[_state_string]
                    if self.envs["STATIC_SUBJECT_STRING"] is not None
                    else ""
                )
                + (
                    (  # # Appends User's State whenever _presence_ctx is zero or otherwise, append the activity's application name.
                        self.envs[
                            "%s_STATUS_STRING"
                            % self._user_ctx["statuses"]["status"].name.upper()
                        ]
                    )
                    if not _contains_activities
                    else _presence_ctx[_preferred_activity]["name"]
                )
                + (  # # Append the seperator. This one is condition-hell since we have to consider two other values and the state of the badge.
                    (
                        _seperator  # ! Seperator #1
                        + (
                            _presence_ctx[_preferred_activity][
                                "state"
                                if self.envs["PREFERRED_PRESENCE_CONTEXT"]
                                is ContextOnSubject.STATE
                                else "details"
                            ]
                        )
                    )
                    if _preferred_activity
                    == PreferredActivityDisplay.RICH_PRESENCE.name
                    and self.envs["PREFERRED_PRESENCE_CONTEXT"]
                    is not ContextOnSubject.CONTEXT_DISABLED
                    else ""
                )
            )

            if (
                self.envs["TIME_DISPLAY_OUTPUT"]
                is not PreferredTimeDisplay.TIME_DISABLED
                and _contains_activities
            ):
                _status_output += _seperator  # ! Seperator #2

                # Handle if the preferred activity exists or otherwise.
                _has_remaining: Union[None, str] = _presence_ctx[_preferred_activity][
                    "timestamps"
                ].get("end")

                _start_time: datetime = datetime.fromtimestamp(
                    int(_presence_ctx[_preferred_activity]["timestamps"]["start"])
                    / 1000
                )
                _running_time: timedelta = datetime.now() - _start_time

                # Resolve.
                if _has_remaining:
                    _end_time = (
                        datetime.fromtimestamp(int(_has_remaining) / 1000) - _start_time
                    )

                    # ! Keep note, that this one is for Unspecified Activity (Spotify) only!!!
                    # # The development of that case will be on post, since I'm still doing most of the parts.
                    # For that case, we don't need to sterilize it.
                    if (
                        _preferred_activity
                        == PreferredActivityDisplay.UNSPECIFIED_ACTIVITY.name
                    ):
                        _running_time = _running_time - timedelta(
                            microseconds=_running_time.microseconds,
                        )
                        _end_time = _end_time - timedelta(
                            microseconds=_end_time.microseconds
                        )

                        _status_output += f"{_running_time} of {_end_time}"

                else:
                    # # We can do the MINUTES_ONLY, SECONDS_ONLY and HOURS_ONLY in the future. But for now, its not a priority and its NotImplemented.
                    _parsed_time = int(_running_time.total_seconds() / 60)

                    # Calculate if some left over minutes can still be converted to hours.
                    _hours = 0
                    _minutes = 0
                    _seconds = 0

                    # * Timedelta() only returns seconds and microseconds. Sadly we have to the computation on our own.
                    while True:
                        if _parsed_time / 60 >= 1:
                            _hours += 1
                            _parsed_time -= 60
                            continue

                        break

                    _minutes = _parsed_time

                    # Resolve time strings based on numbers.
                    # ! This costs us readibility.
                    for idx, each_time_string in enumerate(TIME_STRINGS):
                        if self.envs["TIME_DISPLAY_SHORTHAND"]:
                            TIME_STRINGS[idx] = each_time_string[0]

                        # * We have to handle if we should append postfix 's' if the value for each time is greater than 1 or not.
                        else:
                            TIME_STRINGS[idx] = (
                                each_time_string[:-1]
                                if locals()[f"_{each_time_string}"] < 1
                                else each_time_string
                            )

                    self.logger.debug(
                        f"Resolved Time Output: {_hours} %s {_minutes} %s {_seconds} seconds."
                        % (TIME_STRINGS[0], TIME_STRINGS[1])
                    )

                    is_time_displayable: bool = _hours >= 1 or _minutes >= 1

                    _status_output += (
                        (
                            (f"{_hours} %s" % TIME_STRINGS[0] if _hours >= 1 else "")
                            + (" " if _hours and _minutes else "")
                            + (
                                f"{_minutes} %s" % TIME_STRINGS[1]
                                if _minutes >= 1
                                else ""
                            )
                            + (
                                f" %s"
                                % self.envs[
                                    "TIME_DISPLAY_%s_OVERRIDE_STRING" % "ELAPSED"
                                    if not _has_remaining
                                    else "REMAINING"
                                ]
                            )
                        )
                        if is_time_displayable
                        else "Just started."
                    )

                self.logger.debug(
                    f"Application is identified to be running with remaining time. And is currently under {_running_time} / %s."
                    % (_end_time)
                    if _has_remaining
                    else f"The application is running endless and has been opened for {_running_time}."
                )

            self.logger.debug(
                f"Activity Context (Chosen or Preferred) > {_preferred_activity}"
            )
            self.logger.debug(f"Subject Output > {_subject_output}")
            self.logger.debug(f"State Output > {_state_string}")
            self.logger.debug(f"Status Output > {_status_output}")
            self.logger.debug(f"Final Output > {_subject_output} | {_status_output}")

            # ! Since we are done with the construction of the output. It's time to manage the colors.
            # * I know that _state_string is similar to this case. But I want more control and its reasonable to re-implement, because its main focus was to display a string.
            _status_color: ColorHEX = ColorHEX(
                (
                    self.envs[
                        "%s_COLOR" % _state_string.removesuffix("_STRING")
                        + (
                            ""
                            if _preferred_activity
                            == PreferredActivityDisplay.RICH_PRESENCE.name
                            or _contains_activities
                            else ""
                        )
                    ]
                )
                if self.envs["STATIC_SUBJECT_STRING"] is not None
                or _contains_activities
                else BADGE_NO_COLOR_DEFAULT
            )

            if _status_color.startswith("#"):
                _status_color = ColorHEX(_status_color[1:])

            _subject_color: ColorHEX = ColorHEX(
                self.envs[
                    "%s_COLOR"
                    % (
                        "%s_STATUS" % self._user_ctx["statuses"]["status"].name.upper()
                        if _contains_activities
                        or self.envs["STATIC_SUBJECT_STRING"] is None
                        else _state_string.removesuffix("_STRING")
                    )
                ]
            )
            if _subject_color.startswith("#"):
                _subject_color = ColorHEX(_subject_color[1:])

            self.logger.debug(
                f"Status Color: {_status_color} | Subject Color: {_subject_color}."
            )

            if self.envs["SHIFT_STATUS_ACTIVITY_COLORS"]:
                _status_color, _subject_color = _subject_color, _status_color

            # At this point, construct the badge as fully as it is.
            constructed_url: BadgeStructure = BadgeStructure(
                f"{BADGE_BASE_URL}{quote(_subject_output)}/{quote(_status_output)}?color={_subject_color}&labelColor={_status_color}&icon={BADGE_ICON}"
            )

            final_output = BADGE_BASE_MARKDOWN.format(
                self.envs["BADGE_IDENTIFIER_NAME"],
                constructed_url,
                _redirect_url,
            )

            self.logger.info(f"The Badge URL has been generated. Link: {final_output}")

            return final_output

        # todo: Remember to make exceptions beautiful.
        except KeyError as Err:
            self.logger.error(
                f"Environment Processing has encountered an error. Please let the developer know about the following. | Info: {Err} at line {Err.__traceback__.tb_lineno}."
            )
            os._exit(-1)
